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

## Related

- [PRJ-002](../decisions/project/PRJ-002-version-bump-policy.md) — the policy.
- PRJ-004 — annotated tags matching `.pkit/VERSION` (`pkit version tag`).
- [COR-010](../decisions/core/COR-010-resource-lifecycle.md) — semver +
  `requires_backbone` compatibility model the broaden dogfoods.
- `.pkit/cli/README.md` — the `release` command surface entry.
