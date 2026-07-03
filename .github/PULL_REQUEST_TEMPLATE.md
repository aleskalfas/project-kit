Closes #<issue-number>
<!-- The line above must be the first non-comment line of the PR body. For multiple issues: `Closes #42, closes #43.` (the keyword must be repeated — `Closes #42, #43` only closes #42). -->

## What

<!-- One paragraph: what does this PR do? -->

## Why

<!-- Why is this change needed? Link to a use case, finding, or decision (COR-*, PRJ-*) if applicable. -->

## How

<!-- Any non-obvious implementation choices. Skip if the code is self-explanatory. -->

## Checklist

- [ ] Tests added or updated where relevant.
- [ ] New architectural decisions recorded under `.pkit/decisions/`.
- [ ] Tracker state reflects this PR — issue moved to Review (or Done if no review needed), follow-ups filed as new issues.
- [ ] Migration added if a breaking change in kit-owned content.
- [ ] Surface change? If yes, add a changeset declaring the bump — `changie new` or hand-write one under `.changes/unreleased/` (per PRJ-002; see `.pkit/release/README.md`). This PR does **not** edit `.pkit/VERSION` or a component's `version` — the release step writes those on `main`. If not a surface change, drop a `none` changeset or apply the `skip-changeset` label. *(Cutover: the legacy in-branch `pkit version bump <segment>` still works until the release path is retired.)*
