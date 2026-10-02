---
reader: maintainer
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/release.py
        - src/project_kit/changesets.py
        - src/project_kit/versioning.py
        - .changie.yaml
        - .github/workflows/release-pr.yml
        - .github/workflows/release-tag.yml
      record: [COR-010, COR-041, PRJ-002, PRJ-004, ADR-040]
    revalidated:
      at: 2026-10-02T11:03:47Z
      outcome: updated
---

# Release flow — changesets + the release step

*Mechanics for project-kit-the-project's declared, release-driven version
policy. [PRJ-002](../decisions/project/PRJ-002-version-bump-policy.md) carries
the **policy** (what warrants a bump, declare-then-apply, main-only writes);
this README carries the **mechanics** (the changeset file format, the release
command's behaviour, the contributor workflow, and the CI guard). It is
maintainer-facing — project-kit's own release process — and is not propagated
to adopters.*

## The model in one line

A surface-changing PR **declares** version intent in a changeset file; a
release PR on `main` is the **sole writer** of version numbers, computed from
the changesets.

## Changeset files

Changesets live under `.changes/unreleased/` and are consumed at release. Each
names one tier and the semver segment its surface moved:

```yaml
component: backbone          # `backbone`, or an adapter/capability name
kind: minor                  # the semver SEGMENT: patch | minor | major | none
body: Add the `pkit release` command.   # the note (a changelog line)
```

- **`component`** — `backbone` (the `.pkit/VERSION` tier) or a kit-shipped
  component's name (`claude-code`, `project-management`, …). `pkit release`
  rediscovers the valid set from each `package.yaml`, so a changeset naming an
  unknown component is refused.
- **`kind`** — the segment, a **human surface judgment** (PRJ-002 D2), *not*
  inferred from the commit type. `none` declares "this touched a component's
  tree but is not a surface change" (the escape hatch; consumed without moving
  a version).
- **`body`** — the human-readable note; becomes a changelog line.

Several changesets may name the same component (e.g. two PRs each touch the
backbone); the release takes the **highest** segment and lists every note.

### Declaring that a component needs a backbone

A component's `requires_backbone` floor is a version cell, so a feature branch
never writes it (PRJ-002 D1) — yet a branch can make a component depend on
backbone surface. The branch says so in the component's changeset with one
optional field, and the release writes the floor:

```yaml
component: project-management
kind: minor
body: The capability leaves the journal ignore line to the backbone. Upgrade it together with the backbone.
custom:
  requires_backbone: release   # needs the backbone this release ships
```

- **`requires_backbone`** names the backbone the component needs, one of two
  ways. `pkit release apply` raises the lower bound of the component's
  `requires_backbone` range to it (the floor raise, below). Top-level or under
  `custom:`, like `category` and `pr`.
  - **`release`** — the backbone this release ships: the new one when the
    backbone moves in the same release, else the current `.pkit/VERSION`. For a
    need on backbone surface that has not shipped yet — typically a backbone
    change in the same pull request or one merged beside it.
  - **An explicit `X.Y.Z`** — a backbone that has shipped: a release version
    (no pre-release suffix, no leading zero) that the tree **records as
    released** — a `## X.Y.Z — <date>` release heading in `CHANGELOG.md`, or
    the backbone the tree carries — **at or below the current
    `.pkit/VERSION`**. For a need an older backbone already meets — the
    component starts using a command that shipped in `1.144.0`, say — so the
    floor names that backbone instead of the current one down to its patch.
    Quote it: YAML reads an unquoted `1.150` as the number 1.15.
- An explicit version the tree records no release of — `1.148.7`, or a typo
  like `1.14.0` — is refused, with the lowest recorded release above it named.
  The changelog records releases from `1.140.0` on, so a need an older backbone
  meets names `1.140.0`.
- A version **above the current `.pkit/VERSION`** is refused: it would predict
  the release, which is what `release` is for. If `main` released it after the
  branch was cut, update the branch from `main` instead. The bound is against
  the backbone the tree carries — in an adopter's repo, the installed one,
  which a pin or a downgrade can lower. A pending explicit floor above it then
  blocks the release until the backbone is upgraded or the floor lowered. An
  adopter's changelog records its own components' releases, keyed by date, so
  there the explicit version can name only the installed backbone.
- Two paths serve two needs, so pick by where the surface the component uses
  lives: **unreleased** → `release`; **already shipped** → the version that
  shipped it. Several changesets for one component may declare; the floor goes
  to the highest backbone they name.
- When the backbone does not move in that release, `release` names the current
  one — which may lack the change the component needs (a backbone change
  declared `none`, or one merged after the component's). The floor then goes
  to the current version, and `plan` and `apply` say so under the component's
  bump: confirm the surface the component needs shipped in it. An explicit
  version needs no such notice; a `release` declaration keeps it even when an
  explicit one names the same backbone, since its own need may still postdate
  it.
- It belongs on a **version-moving changeset** (`patch` / `minor` / `major`) of
  a **capability or adapter whose range is `">=X.Y.Z,<A.B.C"` or `">=X.Y.Z"`**,
  since a raised floor changes what the component requires, which is surface
  and never ships under an unchanged version. `release` also needs a release
  that ships a release version of the backbone, since no floor is raised to a
  pre-release (a component-only release under a `.pkit/VERSION` of
  `1.150.0rc1` is refused; an explicit, shipped version is not). `pkit release
  lint` refuses the field on a backbone changeset, on a `none` changeset, on an
  unknown component or one with no such range, with any other value, with an
  explicit version that is not one the tree records at or below the current
  backbone, and with `release` against a pre-release backbone; `pkit release
  plan` and `apply` refuse to compute a release from such a changeset rather
  than drop the declaration or write half of it.
- It rides on a **change to that component, or a release of it**: the pull
  request that declares the floor touches the component's tree, or the
  changeset carrying it moves the component's version. The second is the
  correction path — discovering after a release that the component needs a
  backbone it never declared, say — a `patch` changeset carrying only the
  floor, in a pull request that changes nothing else of the component.
  `pkit release check` refuses a floor with neither behind it (the CI guard,
  below).
- The release states the raised floor in the component's changelog entry —
  *Requires backbone >=X.Y.Z.* (below). Say in the changeset's body what the
  adopter must do — typically *upgrade the component together with the
  backbone*.

### Authoring a changeset

Contributors use **changie** — a dev-only tool provisioned through `mise`
(`[tools]` in `mise.toml`) and wrapped by `mise run changeset`:

```
mise run changeset        # or: changie new
```

changie's native `component` / `kind` / `body` fields are exactly the schema
above, and its `fragmentFileFormat` (`.changie.yaml`) names files
`<component>-<kind>-<timestamp>-<random>.yaml` — the random suffix makes
**parallel PRs collision-free**. Its `custom:` prompts write the optional
`category`, `pr` and `requires_backbone` fields (the last a free string —
`release` or a shipped `X.Y.Z` — which the lint checks). A changeset is equally
hand-writable: drop a YAML file with the three keys into `.changes/unreleased/`.

### changie is adopter-invisible

changie is **never** bundled in the wheel, **never** a runtime dependency, and
**never** required to install or use pkit. It is contributor convenience only.
The CI guard and `pkit release` read the **file**, not the tool
(`project_kit.changesets` parses the YAML with the already-present
`ruamel.yaml`); nothing under `project_kit/_kit/`, no `pyproject` runtime
dependency, and no install doc references it.

## Changelog format + language discipline

`pkit release` generates `CHANGELOG.md` in the **[Keep a
Changelog](https://keepachangelog.com)** format with **[Common
Changelog](https://common-changelog.org)** language. This section is the
contract a contributor and a future maintainer follow.

### Format — Keep a Changelog

One section per release, **newest first**, dated, with entries **grouped by
category** under the universal Keep-a-Changelog set:

> `Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`

```markdown
## 1.141.0 — 2026-07-05

### Added
- Ship the `pkit release check` guard. ([#470])

### Changed
- pkit now runs the version each project pins, so one install works everywhere. ([#465])

[#465]: https://github.com/aleskalfas/project-kit/pull/465
[#470]: https://github.com/aleskalfas/project-kit/pull/470
```

### Multi-tier grouping (the load-bearing rule)

project-kit versions **two tiers** — the backbone and each kit-shipped
component (adapter / capability) — but Keep a Changelog assumes *one* version
per section. The reconciliation:

- A release section is **keyed by the backbone version + date** (the same
  identity a backbone tag carries — annotated tags track `.pkit/VERSION` and
  are backbone-only, per PRJ-004).
- A **backbone** entry is written plain. A **non-backbone component** entry is
  **tagged inline** with its name and new version — `**project-management 0.5.0**
  — <entry>` — because its version differs from the section's backbone key.
- A **component-only release** (a component moves but the backbone does not)
  has no backbone version to key on, so the section **keys by date alone** and
  the inline component tags are what surface *which* component(s) moved and to
  what version.
- A component whose `requires_backbone` floor the release raises carries it
  **once**, at the end of the entry of the changeset that set it and before its
  link: `**project-management 0.55.0** — <entry> Requires backbone >=1.150.0.
  ([#1120])`. A period closes an entry that lacks one first; after an entry
  ending in a list, the sentence is its own paragraph. When an explicit version
  and `release` name the same backbone, the explicit one's entry carries it. A
  floor already at or above the declared backbone changes nothing and is not
  mentioned.

**Rationale (do not "fix" this back).** Keying the section on the backbone
version and carrying component versions inline is a **deliberate deviation from
strict one-version-per-section Keep a Changelog**. It keeps the changelog
faithful to the two-tier semver + compatibility model the project dogfoods
(COR-010, which gives the backbone and each component independent version
lines) and to the backbone-only tag identity (PRJ-004). A future maintainer
who "corrects" the changelog to one version per section would break that
alignment — the deviation is intentional.

Note the altitude split: the **format** above (categories, backbone-keyed
section, inline component tags) is what the shipped `pkit release` generator
produces for *every* adopter — it is universal tool behaviour derived from the
two-tier model (COR-010), not an adopter-optional choice. Only the **language**
discipline below (plain, user-facing sentences, no in-body jargon/refs) is an
editorial policy this project layers on top of that output.

### Language — Common Changelog

Each entry is **one plain sentence describing the user-visible outcome**, not
the mechanism:

- Capital start, period end; one sentence.
- **No internal jargon or references in the body** — no ADR / COR / PR numbers,
  no module or shim names the reader can't see. Say what changed *for the
  reader*, not how it was built.
- The **only** reference is a trailing `([#N])` link resolved in a block at the
  foot of the section.

Contrast — before/after, drawn from the `1.140.0` entry:

> ✗ *Fold the `pkit-router` shim's CWD-aware routing into the installed `pkit`
> entry point (ADR-039)…*
>
> ✓ *pkit now automatically runs the version each project pins, so one install
> works everywhere.* `([#465])`

### The changeset fields behind it

Two optional fields on a changeset drive the format:

- **`category`** — the Keep-a-Changelog group above. It is **orthogonal to the
  `kind` segment**: a `patch` may be `Fixed` *or* `Changed`, a `minor` may be
  `Added` *or* `Changed` — **never derive one from the other**. `category` is
  **optional** (defaults to `Changed` at render) and **irrelevant for `none`**
  changesets, which move no version.
- **`pr`** — the PR reference for the `([#N])` link. It is **optional and
  captured at author time**: the release step does *not* derive it, because
  squash / rebase makes the commit→PR mapping unreliable (the same reason
  release tagging is `.pkit/VERSION`-driven, not message-driven). It takes
  **one of two forms**, and `pkit release lint` refuses any other (`#465`,
  `PR 465`, a URL with no number):
  - **The pull request's number** (`465`, quoted or not) — the entry is
    labelled `[#465]` and linked to that pull request of the repository the
    release runs in: `https://github.com/<owner>/<repo>/pull/465`, the owner
    and repository read from the **`origin` remote's URL** (any form git
    records — `https://`, `git@github.com:`, `ssh://`; credentials in the URL
    are never copied into the link). When the address cannot be derived — no
    `origin`, or an `origin` not on `github.com` — the entry **keeps its
    `([#465])` label and no reference line is written**, so it reads as plain
    text rather than a broken link, and `pkit release apply` warns how many
    numbers it left unlinked.
  - **A full URL** (`https://…/pull/465`) — used **verbatim** as the link
    target, its trailing number the `#N` label. Use it for a pull request in
    another repository, or where the repository is not on GitHub.

  **When `pr` is absent the entry simply carries no link** — the format
  degrades gracefully.

Both may be given **top-level** in a hand-written changeset or under changie's
**`custom:`** map (what `changie new` writes); the parser reads either. A
changeset remains fully **hand-writable** — the `category` / `pr` keys are just
two more optional lines:

```yaml
component: backbone
kind: minor
body: pkit now runs the version each project pins, so one install works everywhere.
category: Changed
pr: 465
```

## The release step — `pkit release`

The sole main-only writer of version state (PRJ-002 D3). Run from a **release
PR** a human merges — it is *not* auto-run on every merge.

| Command | Writes? | What |
|---|---|---|
| `pkit release plan` | no | Preview the computed release (which tiers move, to what, and the notes). |
| `pkit release apply` | yes | Consume changesets → compute each tier from current `main` → write versions → broaden `requires_backbone` → raise declared floors → update `CHANGELOG.md` → delete consumed changesets. Confirms first (`--yes` for CI). Tagging is a separate step (below); `--tag`/`--push` opt in. |
| `pkit release merge <pr>` | yes (merges) | Merge a release PR (the sanctioned path — below). Guarded to `release/*` heads; merges only an open, mergeable, green PR as one squash commit whose subject is the PR title — through the base's merge queue where it has one — and deletes the head branch once GitHub reports the PR merged. Does not tag. `--dry-run` reports without merging; `--no-wait` / `--wait-minutes` set how long it waits for a queue. Runs the cross-repository guard first; `--allow-foreign-repo` confirms a merge in another repository than the session's anchor's. |
| `pkit release publish-notes <version>` | no (publishes) | Publish a **notes-only** GitHub Release for tag `v<version>`, body = that version's `CHANGELOG.md` section (below). Idempotent (updates if it exists); **no artifact**. `--dry-run` prints the notes without calling `gh`. Runs the cross-repository guard first; `--allow-foreign-repo` confirms publishing in another repository than the session's anchor's. |
| `pkit release check` | no | The CI guard (below). |
| `pkit release check-shareable <component>` | no | Pre-sharing lint: is a capability ready to be consumed externally-sourced (COR-041)? (below). |

`apply` in order: writes each tier's version (`.pkit/VERSION` for the backbone,
and with it the self-host `.pkit/manifest.yaml`'s `backbone_version:` line,
[PRJ-007](../decisions/project/PRJ-007-release-maintains-self-host-manifest.md);
the `version:` line in a component's `package.yaml`); **broadens**
`requires_backbone` (see below); **raises the declared floors** (below);
prepends a `CHANGELOG.md` entry from the notes, stating each raised floor; and
deletes the consumed changesets. `plan` shows each floor it will raise under
the component's bump.

### The requires_backbone broaden — two shapes (PRJ-002 D4 + #494)

`apply` widens `requires_backbone` upper bounds so a compatibility claim stays
current without hand-editing. Which components it widens depends on **what
moved**, and it is always **widen-only** — it raises an upper bound to cover a
target version, never narrows a range that is already wider. It never touches
a lower bound; that moves only on declaration (the floor raise, below):

- **A backbone release** widens **every** kit-shipped component's upper bound to
  cover the new backbone minor (`<X.(Y+1).0` for a new backbone `X.Y.Z`). This
  is the original PRJ-002 D4 broaden, driven by the *new* backbone version.
- **A component release** (a component moves, the backbone does not) widens each
  **released** component's own upper bound to cover the repo's **current**
  backbone (`.pkit/VERSION`) — the version the author is releasing under and
  tested against. Releasing a capability under backbone X asserts compatibility
  with X, so its declared range comes to include X. This is #494's author-side
  auto-broaden, closing the gap [COR-041](../decisions/core/COR-041-external-source-distribution.md)
  and [ADR-040](../../tech-docs/architecture/decisions/ADR-040-external-source-write-path.md)
  flagged: the author owns an externally-sourced capability's compatibility
  claim, and this keeps it current on release rather than by hand.

The broaden is **keyed on "a component moved under backbone X"**, not on being
project-kit — so it fires the same way in an adopter's own repo releasing its
own capability. Pass **`--no-broaden`** to skip it (both shapes) when an author
deliberately does *not* want to claim the current backbone — e.g. shipping a
patch known-incompatible with the newest backbone; the upper bound then stays
exactly as authored.

### The declared floor raise (PRJ-002 D4; COR-041)

Beside the widen-only upper bound, `apply` raises a **lower bound** — and only
where a changeset declared it (`requires_backbone`, "Declaring that a
component needs a backbone" above). For each such component that the release
moves, it raises the `>=` floor of its `requires_backbone` range to the highest
backbone its changesets name: for `release`, the backbone version the release
ships — the new backbone when the backbone moves, else the current one — and
for an explicit version, that version. PRJ-002 D4 sets this policy for
project-kit's own components; an adopter releasing its own capability runs the
same step, and there the floor is part of the compatibility claim the
capability's author owns
([COR-041](../decisions/core/COR-041-external-source-distribution.md)).

- **Declared, never automatic.** A floor asserts the component no longer works
  on an older backbone, which only the change's author knows; no floor moves
  without a changeset saying so, and a component that declared nothing keeps
  its floor however far the backbone moves.
- **Raise-only.** A floor already at or above the declared backbone is left as
  it is; `plan` says the floor stays, and prints "floor raised to" only when
  the raise changes the range.
- **When the backbone does not move**, `release` resolves to the current
  `.pkit/VERSION`, and `plan` and `apply` add a notice under the component's
  bump: confirm the surface the component needs shipped in that version. A
  pre-release there (`1.150.0rc1`) is refused before anything is written; no
  floor is raised to a pre-release. An explicit version is a shipped release
  version by construction, so it carries neither the notice nor the refusal.
- **In the changelog.** A raise that changes the range is stated at the end of
  the component's changelog entry — *Requires backbone >=X.Y.Z.* — once per
  component, on the entry of the changeset that set the floor: the one naming
  the highest backbone, an explicit version before `release` when both name
  it, else the first by file name ("Multi-tier grouping" above). The release
  notes published from the changelog carry it too.
- **Two range shapes.** Only `">=X.Y.Z,<A.B.C"` — whose upper bound the broaden
  widens — and `">=X.Y.Z"` — which has no upper bound to widen — are raised.
  Any other shape (single-quoted, spaced, the floor not first) is refused up
  front, by the lint and by `plan`. Both rewrites read the top-level key at the
  start of its line, so a comment quoting an older range is never touched.
- **No empty range.** The raise runs after the broaden, and before anything is
  written `apply` computes every raised range in memory as it will write it —
  broadened first when the broaden runs, then raised — and refuses the release
  if one would not admit the floor it now names, since such a range admits no
  backbone. With the broaden that cannot happen; `--no-broaden` does not skip
  the raise (the need was declared), so there an authored upper bound at or
  below the declared backbone refuses the release: drop `--no-broaden` or widen
  the upper bound. An upper bound that admits the declared backbone but not the
  shipped one is left as authored — that is what `--no-broaden` is for — and
  `apply` warns of it under the plan it prints, before it asks to confirm: the
  component then ships beside a backbone its range refuses. (`release plan` runs
  with the broaden, under which no raised range excludes the shipped backbone.)
- The rewrite touches the one `>=X.Y.Z` in place, like the broaden: the upper
  bound and comments survive, and the release PR's `package.yaml` diff stays
  inside what the changeset guard recognises as the release's writes.
  `pkit release plan --json` carries each raise (`requires_backbone_floor` on
  the component's release: the floors `from` and `to`, whether it is `raised`, the `declared`
  backbone and whether the declaration that set it `names_release` — `false`
  for an explicit version — the shipped `backbone` and whether it moves, the
  plan `lines`, and the `changelog` sentence, null when the range does not
  change), which the release-PR workflow prints under the bump; the PR body's
  generated changelog shows the sentence in the component's entry.

**Tagging is a separate, anchored step** (COR-004's each-step-its-own-command
principle — the same reason `version bump` and `version tag` are distinct).
PRJ-004 tags the *committed* `.pkit/VERSION`, so the tag must point at the
release commit, which does not exist yet when `apply` runs. The sequence:

    pkit release apply                 # on the release branch: write versions + changelog
    # commit the release; open the release PR to main
    pkit release merge <pr>            # merge the release PR (checked; one squash commit, through the queue if any; head branch deleted)
    # release-tag.yml cuts v<new-backbone> on the push to main — or, fully manual:
    pkit version tag --push            # on main: cut v<new-backbone> (PRJ-004)

`apply --tag` is an opt-in shortcut for when HEAD is *already* the release
commit (e.g. re-running on `main` after merge). A component-only release (no
backbone move) cuts no tag — PRJ-004 tags the backbone `.pkit/VERSION`.

### Merging the release PR — `pkit release merge <pr>`

A release PR closes **no issue** — it is a release, not issue work — so the
project-management capability's issue-PR merge gate (`pkit
project-management merge-pr`) legitimately **refuses** it: that gate *requires*
a `Closes #N` reference. That gate is the **universal** pm capability adopters
install, and a "release PR" (the `release/*` branch + `chore(release):` title)
is project-kit's **own** release-flow concept — so baking a release exemption
into the project-neutral issue-PR gate would leak project-specific convention
into it (COR-014). Instead the release flow owns its own merge verb, beside the
`release-pr.yml` that opens the PR and the `release-tag.yml` that tags it.

`pkit release merge <pr>`:

- **Runs the cross-repository guard first** (COR-039; ADR-061 point 6). Once,
  at its entry, before it reads the PR, it compares the session's anchor with
  the repository it runs in, and the clearance covers everything the run
  changes there — the merge or the enqueue, a dequeue, the head branch's
  deletion and the local clean-up. In another repository than the session's
  anchor's it asks at a terminal, and refuses where there is none, merging
  nothing; `--allow-foreign-repo` confirms the merge. With no anchor — a
  release run from a pipeline — there is no session to compare with, the
  guard does not fire, and no flag is needed. `--dry-run` asks nothing: it
  reports how the guard passed, or ends refused, saying a run at a terminal
  would ask. The guard and its residual gaps are the CLI reference's
  (`.pkit/cli/README.md`, "Pull-request commands").
- **Guards to release PRs only.** It refuses unless the PR's head branch is
  `release/*` **and** its title is a `chore(release):` one — a non-release PR is
  refused with a pointer back to `pkit project-management merge-pr`. It is not a
  general issue-PR-gate bypass.
- **Checks preconditions.** The PR must be open, mergeable, and have all
  required checks green; a conflicting, red, or still-running PR is refused with
  a clear reason.
- **Lands through `pkit pull-request land`'s sequence**, by import, and holds
  no copy of it (`.pkit/cli/README.md`, "Pull-request commands"):
  - it plans first: the landing as a dry run, pinned to the head its gates
    read, with `--force` as the landing's `--allow-dropped-head` and
    `--queued-bad-shape warn`;
  - a plan that finds the PR merged, or closed, or cannot read it, or finds
    it already queued — at the checked head, waited for, or at another
    head, taken out of the queue — skips the gates;
  - the landing after a plan that skipped the gates allows no merge and no
    enqueue (`--no-request`): a PR that left the queue between the plan and
    the landing is refused, nothing sent, exit 1, and a re-run plans afresh
    and gates;
  - every other plan runs the gates first, then the plan's own refusal,
    then the landing, which reads the PR again just before its request;
  - `--dry-run` reports from the plan and lands nothing;
  - how the landing ended is read from its end document, decoded strictly
    as a caller of the command decodes it, never from an exit code or the
    landing's in-memory end; an end that does not decode ends the run,
    exit 1, nothing deleted; every word of the report is release's own.
- **Exits by how the landing ended.**
  - `0` — merged, after the clean-up; or closed, nothing to merge. Exit 0
    does not mean merged.
  - `4` — queued, or unconfirmed: nothing deleted, a re-run completes it.
  - `3` — the head moved; the queue dropped the PR; or, no queue seen,
    GitHub never reports it merged once it was merged or queued; nothing
    deleted.
  - `1` — refused, unreadable or failed; a gate refused; or the landing's
    end did not decode.
- **What landing through the sequence changed**, one outcome each:
  - Every run that lands reads the PR once more first: the plan's reading,
    and the squash-commit defaults where the base has a queue.
  - A PR auto-merge holds on a base without a queue is gated, then merged
    directly; it used to be taken for a queued PR and waited for without
    the gates. Its base's requirements met, it merges, exit 0.
  - The same PR, its base's requirements unmet, is refused by gh: exit 1,
    with a warning that auto-merge is still armed and will merge it,
    unpinned, once they are met.
  - A head that moved between release's view and the landing's reading
    exits 3, nothing sent; the pinned request used to fail, exit 1.
  - A base changed after release's view, to one whose queue would not make
    the release's commit, is refused at the landing's reading, exit 1; the
    PR used to be enqueued there.
  - A queue switched on after release's view is found at the landing's
    reading: the defaults are read, and the PR is enqueued; it used to be
    merged directly, which gh turned into an enqueue nothing had judged.
  - A release PR closed without merging after release's view now exits 0,
    "nothing to merge"; gh's refused merge used to exit 1. Exit 0 does not
    mean the release merged: a script that needs to know reads the PR —
    `pkit pull-request read <n> --json`, its `reading.merged` — never the
    exit code.
  - A direct merge GitHub reports merged at another head than the checked
    one deletes the head branch at the head that merged, with a warning,
    exit 0; it used to name the checked head, so the deletion was refused
    and the branch kept.
  - A PR the plan finds queued that leaves the queue before the landing's
    reading is refused, nothing sent, exit 1; release used to wait for it
    and report it dropped, exit 3.
- **Merges** per the project's merge convention: one squash commit on the
  base branch whose subject is the PR title, pinned to the head whose checks
  it read, head branch deleted on merge. The merge is the backbone's one merge
  mechanic (`pkit pull-request`), the one project-management's merge verbs
  land issue PRs with. A merge command that succeeds is not taken for a
  merge: the PR is read again, and only once GitHub reports it merged is the
  head branch deleted — on GitHub by the backbone's deletion (`pkit
  pull-request delete-branch`'s, imported), only while its tip is the head
  the PR merged at, in one compare-and-delete request, so a push made after
  the merge is not lost; then a best-effort local cleanup (switch to the
  base, fast-forward, delete the local head), so a run from a worktree or a
  detached HEAD completes once the merge lands. What became of the remote
  branch is said in one line and does not fail the run: kept — its tip
  moved, another open PR uses it as its head or as its base, or GitHub
  refuses to delete it — not there, or asked for with no answer that tells
  whether it was deleted; where it was not deleted, the line names the
  command that deletes it later (`pkit pull-request delete-branch <n>
  --expect <sha>`). The local head goes only with the remote one — it is
  deleted only once that one was deleted or is gone, and kept, said in one
  line, otherwise — and only when everything on it merged: its tip is the
  head the PR merged at, or behind it; a local head holding commits past it,
  or one this clone cannot compare, is kept with a warning. A merge at a head other than
  the one whose checks were read is warned about. A head that lives in a fork
  is never deleted — its name is the fork author's choice and could name an
  unrelated branch here. No `Closes #N` requirement — a release PR has none.
- **Lands through the merge queue** where the base has one, rather than
  around it. The queue makes the squash commit itself, by its own merge
  method and from the repository's squash-commit defaults, ignoring what a
  merge command passes — so the run refuses, enqueuing nothing, unless the
  queue squashes and the defaults are the PR title and the PR body
  (`PR_TITLE` and `PR_BODY`; set them with `gh api -X PATCH
  repos/{owner}/{repo} -f squash_merge_commit_title=PR_TITLE -f
  squash_merge_commit_message=PR_BODY`). A head the queue already dropped is
  not enqueued again unchanged: its checks may have failed on the merge the
  queue was about to make, or a maintainer may have taken it out on purpose.
  The run refuses, naming when and why the queue dropped it; push a fix and
  run again, or pass `--force` to enqueue the same head again — the rule
  project-management's merge verbs keep. It enqueues the PR pinned to the
  checked head, prints where it stands (`position 2 in the queue, awaiting
  checks, about 5 min to merge`), and waits for the merge — as long as the
  queue estimates plus 2 minutes, at most 30, or `--wait-minutes`. Then:
  - **merged** — the head branch is deleted (at the head that merged), exit 0;
  - **still queued** when the wait ends, or with `--no-wait` at once — exit
    4, nothing deleted; the PR is accepted, and the same command run again
    once it has merged deletes the head branch. A run on a PR already in the
    queue waits for it rather than enqueueing it again — warning when the
    queue would not make the release's squash commit, since the PR lands as
    the queue composes it unless it is taken out first — and a run on a
    merged PR runs only the clean-up;
  - **dropped** by the queue — its checks failed on the merge it was about
    to make, or it no longer merged cleanly — exit 3, with what the queue
    reported; nothing is deleted. Fix it and run again;
  - **head moved** after the checks were read — the PR is taken out of the
    queue, so commits nobody checked do not merge; exit 3, nothing deleted.

  Without a queue the merge is direct, pinned to the checked head; if GitHub
  then reports the PR queued rather than merged (a queue switched on
  meanwhile), it is waited for as above, and if GitHub cannot be read to
  confirm the merge the run exits 4 with nothing deleted, for a re-run to
  complete. A direct merge gh accepted that GitHub never reports merged
  exits 3, naming the PR's state — nothing is deleted.

  Every `gh` call is bounded, the reading of the release PR among them, so
  no stuck call holds the run. A merge or an enqueue that gets no answer is
  settled by reading the PR (`.pkit/cli/README.md`, "Pull-request
  commands"): made, the run goes on as it would; not seen made on two
  readings, it refuses, exit 1, saying what the readings saw and that this
  run saw nothing merged — never that nothing merged, since GitHub may still
  apply the request — and naming the reading (`pkit pull-request read <n>`)
  and the re-run that tell; and when GitHub cannot be read since, the run
  says so plainly — what was asked, that whether it was made is not known,
  and the command that reads the PR — claiming neither that the release
  merged nor that it did not, and exits 4 with nothing deleted, for a run
  once GitHub answers to complete. A run that cannot read the release PR —
  its view answered with something that is not JSON among it — or how its
  base merges, before it asks anything says that this run asked nothing; so
  does one whose view names the head in another form than a full commit id,
  which the landing refuses before it reads. When the head moved while the PR was queued and the queue merged
  it before it could be taken out, the run says it merged, and at which head,
  exit 3, nothing deleted; a re-run deletes the head branch.
- **Does not tag.** `release-tag.yml` cuts the backbone tag on the resulting
  push to `main` (VERSION-driven, PRJ-004); the merge and the tag stay split.
- **Is idempotent**: on a closed PR it reports there is nothing to merge, and
  on a merged one it runs only the clean-up — neither is an error. It derives
  the repo from the ambient `gh` context (no hardcoded owner/repo), so it is
  project-neutral.

It stays **human-gated**: a human decides to run it; nothing auto-merges.

### Release notes — `pkit release publish-notes <version>`

Cutting a release leaves a bare git tag; the GitHub release page
(`…/releases/tag/vX`) then shows nothing about *what changed*. `pkit release
publish-notes <version>` fills that gap: it extracts that version's
`CHANGELOG.md` section (the lines from its `## <version> …` heading up to the
next release heading, including the section's trailing `[#N]:` link block) and
publishes it as the body of a GitHub Release for tag `v<version>`.

- **Notes only — never an artifact (the guard).** The Release carries **no
  file, tarball, or wheel**, and does not use `--generate-notes` (the section
  is supplied verbatim). The no-artifact posture is project-kit's distribution
  choice — see **PRJ-004** for the why; in short, install stays the git URL at a
  tag, and the Release is a **notes overlay** on that tag, never an
  artifact/download channel. Do not add an upload.
- **Idempotent.** Re-running **updates** the Release's notes rather than
  erroring; it creates the Release the first time and edits it thereafter. A
  **missing tag is a clear error** (the create path passes `--verify-tag`, so
  `gh` refuses to publish notes for a tag that does not exist).
- **`--dry-run`** prints the notes it would publish without calling `gh`.
- **Project-neutral.** The repo is derived from the ambient `gh` context (the
  git remote in the working directory), with no hardcoded owner/repo — the same
  discipline as `pkit release merge`.
- **Runs the cross-repository guard first**, at its entry, as `pkit release
  merge` does: in another repository than the session's anchor's it asks at a
  terminal and refuses without one, publishing nothing, unless
  `--allow-foreign-repo` confirms it; in a pipeline, with no anchor, it needs no
  flag. `--dry-run` never asks. So does `pkit version tag --push` — and
  `version untag --push`, and `release apply --tag --push` — before the tag
  is made or pushed; a tag made only locally runs no guard.

It slots into the sequence after the tag is cut:

    pkit version tag --push            # on main: cut v<new-backbone> (PRJ-004)
    pkit release publish-notes <new-backbone>   # notes-only Release for that tag

In CI this runs automatically inside `release-tag.yml` (below), right after the
tag is cut.

## Automated flow (CI)

Two workflows under `.github/workflows/` turn the manual sequence above into a
human-gated automation. They **never auto-merge** — a human reviews the release
PR and merges it with `pkit release merge <pr>` (the sanctioned path above); the
automation only proposes and, post-merge, tags.

**1. `release-pr.yml` — open the release PR.** Triggered by `workflow_dispatch`
(manual) or a weekly `schedule`. It:

- Computes the release from the pending changesets (`pkit release plan --json`)
  and **no-ops cleanly** when nothing moves a version (an empty release, or only
  `none` changesets — those wait for the next real release rather than opening a
  version-less PR).
- Creates a `release/v<new-backbone>` branch off `main`, runs `pkit release
  apply --yes` (versions + broaden + declared floors + `CHANGELOG.md`,
  consuming the changesets), commits `chore(release): v<new-backbone>`, pushes,
  and opens a **release PR** whose body shows the computed bumps — each with
  the floor raise a changeset declared for it, as `plan` prints it — and the
  generated changelog, raised floors included, for review.
- Is **idempotent**: if a release PR is already open (any head under
  `release/`), it skips rather than opening a duplicate.
- Does **not** tag — the tag must point at the *merged* release commit (PRJ-004),
  which does not exist until the human merges. Tagging is workflow 2.

**2. `release-tag.yml` — tag + notes post-merge.** Runs on `push` to `main`.
Detection is **VERSION-driven, not message-driven** (a release PR may land as a
merge, squash, or rebase, so the head commit's message is unreliable): if the
tag matching `.pkit/VERSION` does not yet exist, it cuts it via `pkit version
tag --push`, then — **only when it just cut a tag** — publishes the notes-only
GitHub Release for that version via `pkit release publish-notes` (body = the
`CHANGELOG.md` section; **no artifact**, per the guard above). Naturally
**idempotent** — a non-release push doesn't change `.pkit/VERSION`, so that
version's tag already exists, the publish step is skipped, and the job no-ops.
Backbone tag only (per-component tags were dropped by design, PRJ-004).

### One-time repo setup (enable the automation)

Before the first automated release, enable one repository setting — without it
`release-pr.yml` fails at `gh pr create` with *"GitHub Actions is not permitted
to create or approve pull requests"* (observed cutting v1.140.0):

- [ ] **Settings → Actions → General → Workflow permissions** → check **"Allow
  GitHub Actions to create and approve pull requests."** This is a repo/org
  toggle that gates *every* Actions-created PR; the workflow's own
  `pull-requests: write` permission is necessary but **not sufficient** without
  it.
- [ ] *(Optional, recommended)* add a **`RELEASE_PAT`** secret so `checks.yml`
  runs on the release PR automatically — see Token handling below. Without it the
  release PR still opens; its CI just has to be kicked manually.

That is the whole setup — both workflows already ship in `.github/workflows/`;
nothing else is needed to turn the automation on for a repo.

### Token handling (read before relying on downstream CI)

The default `GITHUB_TOKEN` opens the release PR, but by GitHub's loop-prevention
rule a PR it opens does **not** trigger `on: pull_request` workflows — so
`checks.yml` would not auto-run on the release PR. Two ways this is handled:

- **Preferred:** set a repo/environment secret **`RELEASE_PAT`** (a PAT or
  fine-grained token with `contents` + `pull-requests` write). `release-pr.yml`
  uses it when present, so the PR triggers `checks.yml` normally.
- **Without it:** the workflow still works; a maintainer kicks the PR's checks
  (re-run or an empty commit), and `checks.yml` runs on `push` to `main` after
  the merge regardless. Pushing the tag with `GITHUB_TOKEN` likewise won't fire
  a future `on: push: tags:` workflow — there are none today; `RELEASE_PAT`
  covers that case if one is added.

Workflow permissions are minimal: `release-pr.yml` gets `contents: write`
(branch) + `pull-requests: write` (the PR); `release-tag.yml` gets `contents:
write` (the tag **and** the notes-only Release — both are `contents`). Neither
has merge authority.

### Migration-dir prediction warning (#465)

Migration dirs are named `<X.Y.0>` and authored in the same change-set as the
surface they migrate (COR-010) — so the name *predicts* the release version
before the release computes it. `pkit release plan` (and `apply`) warn when a
backbone migration dir above the current `.pkit/VERSION` does **not** match the
computed release version — an orphaned prediction (the coupling flagged on
\#465). The warning is **non-fatal** (surface is a human judgment) and rides
along in the release PR body via the `--json` summary's `migration_warnings`.

### Cutover — the old path still works

This is the **introduce** step of introduce → migrate → retire. `pkit version
bump <segment>` (and its `tag` / `unbump` / `--pre` siblings) is unchanged and
fully functional; the release step *adds* the declare-then-apply path beside
it. Both broaden `requires_backbone` today (broadening is idempotent), so the
two coexist safely; only the release step raises a declared floor, since only
it reads changesets. Retiring in-branch bumping — once the release path is
trusted — is a downstream change.

## The surface-without-changeset CI guard

`pkit release check [--base <ref>]` fails a PR that touches a component's
surface but adds no changeset for it. The diff runs from where the branch left
its base: `--base`, else `$PKIT_CHECK_BASE`, else the project's default branch
(COR-054; `pkit repository base` shows it). Wired as a PR-scoped step in
`.github/workflows/checks.yml` (it needs the PR base ref and PR labels, which a
local pre-push hook lacks — so it is not in `scripts/check.sh`). Run it locally
with `pkit release check`.

**What a green surface check means.** Every component whose surface the diff
touches is named by a changeset the diff itself carries — a file under
`.changes/unreleased/` it adds, edits or renames — or an escape hatch or the
release-PR exemption (below) waived the check. A pending changeset the diff
leaves alone does not count, even when it names the same component: one an
earlier PR merged, or one merging the base brought onto the branch, declares
that PR's change, not this one's. Editing a pending changeset counts whatever
the edit — the guard reads which files the diff changes, not what changed in
them — so extending a pending changeset's note to cover this change declares
it; review judges whether the note does. The diff is committed work only: a
changeset not yet committed is not in it.

**A declared floor rides on its component or a release of it (PRJ-002 D4).**
From the same diff, the guard also fails a PR that declares a
`requires_backbone` floor for a component it neither touches nor moves:

- **Declares** — the PR adds or edits a changeset, and the floor it carries
  differs from the one the file held at the merge base (added, or its value or
  component changed). A note-only edit of a pending floor changeset, or a
  re-quoting, declares nothing and is not judged; a pending changeset an
  earlier PR merged was judged on that PR.
- **Touches** — any changed file under the component's subtree, the same path
  heuristic as the surface check. A README-only or comment-only edit counts:
  the guard cannot tell it from a code change, so it holds a declaration to a
  diff, not to the truth of the need, which review judges.
- **Moves** — the changeset carrying the floor is `patch` or above. That is the
  correction path: a need found after the component shipped, declared in a
  floor-only `patch` changeset for it, passes although the PR touches nothing
  of the component.

What is left is a floor on a `none` changeset for a component the PR leaves
alone — which the lint also refuses, whatever the diff, since a `none`
changeset may not carry a floor (check 3 below); what the guard adds is the
pull request that declared it. **No escape
hatch waives this check**: the `skip-changeset` label and the release-PR
exemption below both waive the surface check only, and a release diff only
deletes changesets, so it declares no floor.

**Escape hatches for the surface check** (so trivia / docs PRs aren't forced
into ceremony):

1. A **`none` changeset** naming the component, carried by the PR like any
   other — an in-repo, reviewable "not a surface change" declaration.
2. The **`skip-changeset` label** — surfaced to the guard as
   `PKIT_CHANGESET_SKIP=1`; passes the surface check unconditionally.

**Release-PR exemption (automatic, no label).** A release PR *is*
`pkit release apply`'s output — it bumps `.pkit/VERSION` and each moving
`package.yaml`, rewrites `requires_backbone` lines (the broaden and any declared
floor), moves the self-host `.pkit/manifest.yaml`'s `backbone_version` on a
backbone release, prepends `CHANGELOG.md`, and **deletes** the consumed
`.changes/unreleased/*` changesets. That diff would trip the guard (VERSION and
`package.yaml` are surface) while the changesets it would need are exactly the
ones it just consumed. The guard recognises a release diff **by its content**,
against one list of what a release writes (`release_writes` in
`project_kit/release.py`), made of the files and line patterns the release step
writes through — each file, the status the write leaves, and, for a file
rewritten in place, the only lines it changes, through the patterns the
writers rewrite them by (a `package.yaml`'s `version:` line and a
`requires_backbone:` range the broaden widens or a declared floor raises, the
manifest's `backbone_version:`). A diff that is *only* those writes, and more
than the consumed changesets, is the release itself, not a new surface change,
and passes the surface check with no `skip-changeset` label. The signal is the
content rather than the branch name, so it is self-contained (works locally
and in CI, on any branch, in any adopter's repo) and a branch named `release/*`
does not produce it; CI raises no hatch for one. It is strict — a single stray
file or line outside the list (a `src/` edit riding along, a manifest line
beside `backbone_version`, a `requires_backbone` range the release never
writes, such as `"*"`) makes the diff no longer the release, so the guard
runs normally and the exemption can never smuggle real surface through. A write
the release step gains joins the list in the same change; otherwise the guard
fails the next release PR that makes it.

**Limits (read this).** Surface is ultimately a **human judgment** (PRJ-002
D2); the guard is a **path heuristic** and cannot be exact:

- It **false-positives** — a README-only or comment-only edit under a
  component subtree, or under a backbone-surface prefix, trips it even though no
  surface moved. Override with a `none` changeset or the label.
- It **false-negatives** — a genuine surface change expressed only in a path
  outside the heuristic's prefixes (see `BACKBONE_SURFACE_PREFIXES` in
  `project_kit/release.py`) slips through. The guard is a reminder, not a
  proof; reviewers still judge surface.
- **Decision-only PRs** (a COR / PRJ / ADR / DEC) trip the guard on purpose —
  `.pkit/decisions/` is a backbone-surface prefix. Declare **`none`** for a
  *design-ahead* decision (the feature ships in a later implementation PR that
  carries the real changeset) or a **real** changeset for a *self-executing*
  rule change (its text is itself an adopter-observable behaviour change). The
  design-ahead-vs-self-executing test is spelled out in PRJ-002.

The backbone-surface prefixes and per-component subtrees are reviewable data in
`project_kit/release.py` — tune them as the tree evolves.

## The changeset + changelog format lint

`pkit release lint` validates the **objective, mechanically-checkable subset**
of the format contract above. It is a *format* check distinct from the surface
guard: the guard asks "does a surface change carry a changeset?"; the lint asks
"is the changeset / changelog **well-formed**?". It reads committed files only
(no PR base ref, no labels), so — unlike `release check` — it rides in the
shared aggregator (`scripts/check.sh`), which both the local pre-push hook and
`checks.yml` run. Run it locally with `pkit release lint`.

**What it checks (objective only):**

1. **Changeset category and `pr`** — when a changeset carries a `category`, it
   must be one of the Keep-a-Changelog groups (`Added` · `Changed` ·
   `Deprecated` · `Removed` · `Fixed` · `Security`). Absent is fine (it
   defaults at render); an *unknown* category fails. When it carries a `pr`, it
   must be the pull request's number (`465`) or an `http(s)://` URL ending in
   it — the two forms the renderer links (see "The changeset fields behind it"
   above); anything else (`#465`, `PR 465`, `0465`, a URL with no number)
   fails. Absent is fine.
2. **Changeset body** — for a version-moving changeset (not `none`), the body
   must be non-empty, **not solely a bare reference** (`#478` / `ADR-013` /
   `DEC-001` / `COR-010` / a bare URL — the objective proxy for "no
   jargon-only entry"), start capitalized, and end with a period. A `none`
   changeset produces no changelog line, so its body is not linted (its
   category and `pr` still are).
3. **Changeset floor field** — a `requires_backbone` field must say `release`
   (in a release that ships a release version of the backbone) or name a
   release version the tree records (a `CHANGELOG.md` release heading, or the
   backbone it carries) at or below the current `.pkit/VERSION`, on a
   version-moving changeset of a capability or adapter whose
   `requires_backbone` is `">=X.Y.Z,<A.B.C"` or `">=X.Y.Z"`. It fails on the
   backbone, on a `none` changeset, on an unknown component or one with no
   floor in that shape to raise, on any other value — an explicit version
   above the current backbone, one the tree records no release of, a
   pre-release, or one with a leading zero included; an unquoted `1.150`,
   which YAML reads as a number, is reported as written, with a hint to quote
   it — and, for `release`, when the backbone the release would ship is a
   pre-release — the same check `release plan` / `apply` refuse on, so the
   lint reports it before the release does. An empty value declares no floor.
   A `.pkit/VERSION` that holds no version is reported once, at that file,
   since no floor can be checked against it. Whether the PR declared the
   floor on a change to the component or a release of it is the guard's
   check, not the lint's: the lint reads no diff. The components are read only
   when a changeset carries the field. **The escape hatch does not cover this
   check**: it is the release's own refusal, reported early, and an invalid
   field blocks every later release on `main` until it is fixed.
4. **`CHANGELOG.md` structure** — release-section (`## `) headings match the
   generator's shape (`## <version> — <date>` or a date-only `## <date>`; the
   canonical KaC `## [<version>] - <date>` is also accepted), and every
   category (`### `) heading is a known group. Only heading **structure** is
   checked — the entry text itself is not.

**What it does NOT check (and why).** It makes **no attempt** at the
plain-language / no-in-body-jargon discipline (the "Language — Common
Changelog" section above). Whether an entry is a plain, user-facing sentence
free of internal jargon is **human judgment**, left to the guide and to review
— exactly the line the surface guard draws for "is this a surface change?".

**Limits (read this).** Like the surface guard, the lint is a **reminder, not
a proof**:

- The capital-start check **false-positives** on a legitimate entry that opens
  with an inherently lowercase identifier (e.g. an entry beginning `pkit …`, as
  the `1.140.0` changelog entry does — that entry is *not* linted because the
  lint reads changelog *structure* only, but a changeset body written the same
  way would trip it). Override with the escape hatch.
- It cannot judge whether a well-formed sentence is *actually* plain and
  jargon-free — a body that is grammatically perfect but full of module names
  passes the lint and is caught only in review.

**Escape hatch:** `pkit release lint --skip`, or set `PKIT_CHANGELOG_LINT_SKIP`
(any of `1`/`true`/`yes`) — passes the format checks unconditionally, for the
rare case an objective rule mis-fires. It does not pass an invalid floor field
(check 3).

The category set and heading shapes are reviewable constants in
`project_kit/release.py` (`CHANGELOG_CATEGORIES` and the heading regexes).

## The shareability check — `pkit release check-shareable <component>`

A **pre-sharing lint**: before a capability is shared to be consumed
**externally-sourced** ([COR-041](../decisions/core/COR-041-external-source-distribution.md)),
verify it is ready. A consumer pulls the capability **whole at a pin**, reads its
manifest, and gates compatibility on the declared `requires_backbone` range
against the consumer's own backbone
([ADR-040](../../tech-docs/architecture/decisions/ADR-040-external-source-write-path.md)
point 4). For that to work the capability must declare the pieces the consumer's
gate reads — this checks that objective subset and reports **pass or the
specific gaps**:

- **A `version`** — a consumer pins by version, so the manifest must declare a
  non-empty `component.version`.
- **A well-formed manifest** — the `package.yaml` must parse as a YAML mapping
  with a `component:` block.
- **A bounded `requires_backbone` range** — a `>=LOW,<HIGH` form the consumer's
  compatibility gate can evaluate. An unbounded or open form (`*`, a bare
  `>=X`) cannot gate a backbone and is flagged.

It also **warns** (non-blocking) on cheaply-detectable **local-only
assumptions** — an absolute filesystem path or a `file://` URL in the manifest,
which a consumer will not have. That is a **heuristic reminder, not a proof**;
deeper local-only coupling in scripts is human judgment left to review.

```
pkit release check-shareable <capability-name>
```

It **checks any component by name** and is **project-neutral** — no hardcoded
project-kit specifics — so an adopter runs it on their own capability before
sharing it across their repos. The backbone tier is not a shareable component
and is refused; an unknown name is a clear usage error.

## Related

- [COR-041](../decisions/core/COR-041-external-source-distribution.md) —
  externally-sourced distribution; the author owns the compatibility claim the
  component-release broaden keeps current and the shareability check verifies.
- [PRJ-002](../decisions/project/PRJ-002-version-bump-policy.md) — the policy.
- PRJ-004 — annotated tags matching `.pkit/VERSION` (`pkit version tag`).
- [COR-010](../decisions/core/COR-010-resource-lifecycle.md) — semver +
  `requires_backbone` compatibility model the broaden dogfoods.
- `.pkit/cli/README.md` — the `release` command surface entry.
