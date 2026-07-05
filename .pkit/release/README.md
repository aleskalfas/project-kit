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
| `pkit release check` | no | The CI guard (below). |

`apply` in order: writes each tier's version (`.pkit/VERSION` for the backbone,
the `version:` line in a component's `package.yaml`); **broadens** kit
components' `requires_backbone` upper bound driven by the new backbone version
(PRJ-002 D4 — the broaden moves here, out of per-branch `version bump`);
prepends a `CHANGELOG.md` entry from the notes; and deletes the consumed
changesets.

**Tagging is a separate, anchored step** (COR-004's each-step-its-own-command
principle — the same reason `version bump` and `version tag` are distinct).
PRJ-004 tags the *committed* `.pkit/VERSION`, so the tag must point at the
release commit, which does not exist yet when `apply` runs. The sequence:

    pkit release apply                 # on the release branch: write versions + changelog
    # commit the release; open/merge the release PR to main
    pkit version tag --push            # on main: cut v<new-backbone> (PRJ-004)

`apply --tag` is an opt-in shortcut for when HEAD is *already* the release
commit (e.g. re-running on `main` after merge). A component-only release (no
backbone move) cuts no tag — PRJ-004 tags the backbone `.pkit/VERSION`.

## Automated flow (CI)

Two workflows under `.github/workflows/` turn the manual sequence above into a
human-gated automation. They **never auto-merge** — a human reviews and merges
the release PR; the automation only proposes and, post-merge, tags.

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

**2. `release-tag.yml` — tag post-merge.** Runs on `push` to `main`. Detection
is **VERSION-driven, not message-driven** (a release PR may land as a merge,
squash, or rebase, so the head commit's message is unreliable): if the tag
matching `.pkit/VERSION` does not yet exist, it cuts it via `pkit version tag
--push`. Naturally **idempotent** — a non-release push doesn't change
`.pkit/VERSION`, so that version's tag already exists and the job no-ops.
Backbone tag only (per-component tags were dropped by design, PRJ-004).

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
write` (the tag). Neither has merge authority.

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

## Related

- [PRJ-002](../decisions/project/PRJ-002-version-bump-policy.md) — the policy.
- PRJ-004 — annotated tags matching `.pkit/VERSION` (`pkit version tag`).
- [COR-010](../decisions/core/COR-010-resource-lifecycle.md) — semver +
  `requires_backbone` compatibility model the broaden dogfoods.
- `.pkit/cli/README.md` — the `release` command surface entry.
