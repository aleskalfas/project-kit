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

### Authoring a changeset

Contributors use **changie** — a dev-only tool provisioned through `mise`
(`[tools]` in `mise.toml`) and wrapped by `mise run changeset`:

```
mise run changeset        # or: changie new
```

changie's native `component` / `kind` / `body` fields are exactly the schema
above, and its `fragmentFileFormat` (`.changie.yaml`) names files
`<component>-<kind>-<timestamp>-<random>.yaml` — the random suffix makes
**parallel PRs collision-free**. A changeset is equally hand-writable: drop a
YAML file with the three keys into `.changes/unreleased/`.

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
  release tagging is `.pkit/VERSION`-driven, not message-driven). The value is
  used **verbatim** as the link target (the shipped generator is
  project-neutral and cannot synthesise a repo URL), and its trailing number
  is the `#N` label — so **give a full PR URL for a live link**; a bare number
  still labels the entry but resolves to a non-linking reference. **When `pr`
  is absent the entry simply carries no link** — the format degrades
  gracefully.

Both may be given **top-level** in a hand-written changeset or under changie's
**`custom:`** map (what `changie new` writes); the parser reads either. A
changeset remains fully **hand-writable** — the `category` / `pr` keys are just
two more optional lines:

```yaml
component: backbone
kind: minor
body: pkit now runs the version each project pins, so one install works everywhere.
category: Changed
pr: https://github.com/aleskalfas/project-kit/pull/465
```

## The release step — `pkit release`

The sole main-only writer of version state (PRJ-002 D3). Run from a **release
PR** a human merges — it is *not* auto-run on every merge.

| Command | Writes? | What |
|---|---|---|
| `pkit release plan` | no | Preview the computed release (which tiers move, to what, and the notes). |
| `pkit release apply` | yes | Consume changesets → compute each tier from current `main` → write versions → broaden `requires_backbone` → update `CHANGELOG.md` → delete consumed changesets. Confirms first (`--yes` for CI). Tagging is a separate step (below); `--tag`/`--push` opt in. |
| `pkit release merge <pr>` | yes (merges) | Merge a release PR (the sanctioned path — below). Guarded to `release/*` heads; merges only an open, mergeable, green PR; squash + delete-branch. Does not tag. `--dry-run` reports without merging. |
| `pkit release publish-notes <version>` | no (publishes) | Publish a **notes-only** GitHub Release for tag `v<version>`, body = that version's `CHANGELOG.md` section (below). Idempotent (updates if it exists); **no artifact**. `--dry-run` prints the notes without calling `gh`. |
| `pkit release check` | no | The CI guard (below). |
| `pkit release check-shareable <component>` | no | Pre-sharing lint: is a capability ready to be consumed externally-sourced (COR-041)? (below). |

`apply` in order: writes each tier's version (`.pkit/VERSION` for the backbone,
the `version:` line in a component's `package.yaml`); **broadens**
`requires_backbone` (see below); prepends a `CHANGELOG.md` entry from the notes;
and deletes the consumed changesets.

### The requires_backbone broaden — two shapes (PRJ-002 D4 + #494)

`apply` widens `requires_backbone` upper bounds so a compatibility claim stays
current without hand-editing. Which components it widens depends on **what
moved**, and it is always **widen-only** — it raises an upper bound to cover a
target version, never narrows a range that is already wider:

- **A backbone release** widens **every** kit-shipped component's upper bound to
  cover the new backbone minor (`<X.(Y+1).0` for a new backbone `X.Y.Z`). This
  is the original PRJ-002 D4 broaden, driven by the *new* backbone version.
- **A component release** (a component moves, the backbone does not) widens each
  **released** component's own upper bound to cover the repo's **current**
  backbone (`.pkit/VERSION`) — the version the author is releasing under and
  tested against. Releasing a capability under backbone X asserts compatibility
  with X, so its declared range comes to include X. This is #494's author-side
  auto-broaden, closing the gap [COR-041](../decisions/core/COR-041-external-source-distribution.md)
  and [ADR-040](../../docs/architecture/decisions/ADR-040-external-source-write-path.md)
  flagged: the author owns an externally-sourced capability's compatibility
  claim, and this keeps it current on release rather than by hand.

The broaden is **keyed on "a component moved under backbone X"**, not on being
project-kit — so it fires the same way in an adopter's own repo releasing its
own capability. Pass **`--no-broaden`** to skip it (both shapes) when an author
deliberately does *not* want to claim the current backbone — e.g. shipping a
patch known-incompatible with the newest backbone; the range then stays exactly
as authored.

**Tagging is a separate, anchored step** (COR-004's each-step-its-own-command
principle — the same reason `version bump` and `version tag` are distinct).
PRJ-004 tags the *committed* `.pkit/VERSION`, so the tag must point at the
release commit, which does not exist yet when `apply` runs. The sequence:

    pkit release apply                 # on the release branch: write versions + changelog
    # commit the release; open the release PR to main
    pkit release merge <pr>            # merge the release PR (checked; squash + delete branch)
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

- **Guards to release PRs only.** It refuses unless the PR's head branch is
  `release/*` **and** its title is a `chore(release):` one — a non-release PR is
  refused with a pointer back to `pkit project-management merge-pr`. It is not a
  general issue-PR-gate bypass.
- **Checks preconditions.** The PR must be open, mergeable, and have all
  required checks green; a conflicting, red, or still-running PR is refused with
  a clear reason.
- **Merges** by squash + delete-branch (the project's merge convention). No
  `Closes #N` requirement — a release PR has none.
- **Does not tag.** `release-tag.yml` cuts the backbone tag on the resulting
  push to `main` (VERSION-driven, PRJ-004); the merge and the tag stay split.
- **Reports cleanly** when the PR is already merged or closed (idempotent — not
  an error), and derives the repo from the ambient `gh` context (no hardcoded
  owner/repo), so it is project-neutral.

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
  apply --yes` (versions + broaden + `CHANGELOG.md`, consuming the changesets),
  commits `chore(release): v<new-backbone>`, pushes, and opens a **release PR**
  whose body shows the computed bumps and the generated changelog for review.
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
two coexist safely. Retiring in-branch bumping — once the release path is
trusted — is a downstream change.

## The surface-without-changeset CI guard

`pkit release check --base <ref>` fails a PR that touches a component's surface
but ships no changeset for it. Wired as a PR-scoped step in
`.github/workflows/checks.yml` (it needs the PR base ref and PR labels, which a
local pre-push hook lacks — so it is not in `scripts/check.sh`). Run it locally
with `pkit release check --base origin/main`.

**Escape hatches** (so trivia / docs PRs aren't forced into ceremony):

1. A **`none` changeset** naming the component — an in-repo, reviewable "not a
   surface change" declaration.
2. The **`skip-changeset` label** — surfaced to the guard as
   `PKIT_CHANGESET_SKIP=1`; passes unconditionally.

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

1. **Changeset category** — when a changeset carries a `category`, it must be
   one of the Keep-a-Changelog groups (`Added` · `Changed` · `Deprecated` ·
   `Removed` · `Fixed` · `Security`). Absent is fine (it defaults at render);
   an *unknown* category fails.
2. **Changeset body** — for a version-moving changeset (not `none`), the body
   must be non-empty, **not solely a bare reference** (`#478` / `ADR-013` /
   `DEC-001` / `COR-010` / a bare URL — the objective proxy for "no
   jargon-only entry"), start capitalized, and end with a period. A `none`
   changeset produces no changelog line, so its body is not linted (its
   category still is).
3. **`CHANGELOG.md` structure** — release-section (`## `) headings match the
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
(any of `1`/`true`/`yes`) — passes unconditionally, for the rare case an
objective rule mis-fires.

The category set and heading shapes are reviewable constants in
`project_kit/release.py` (`CHANGELOG_CATEGORIES` and the heading regexes).

## The shareability check — `pkit release check-shareable <component>`

A **pre-sharing lint**: before a capability is shared to be consumed
**externally-sourced** ([COR-041](../decisions/core/COR-041-external-source-distribution.md)),
verify it is ready. A consumer pulls the capability **whole at a pin**, reads its
manifest, and gates compatibility on the declared `requires_backbone` range
against the consumer's own backbone
([ADR-040](../../docs/architecture/decisions/ADR-040-external-source-write-path.md)
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
