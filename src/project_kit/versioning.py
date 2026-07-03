"""Version-bump + tag implementation per PRJ-002 + PRJ-004.

`bump_version` mirrors the bash dispatcher's `cmd_version_bump`:
bumps `.pkit/VERSION` and broadens the `requires_backbone` upper bound
on every kit-shipped `package.yaml` whose existing range no longer
includes the new backbone version. Idempotent on patch bumps within
the existing minor line; reports each broaden inline.

`tag_version` automates the per-PRJ-002/-004 tag-on-bump convention:
reads `.pkit/VERSION`, tags HEAD as `v<version>`, optionally pushes
to `origin`. The previous workflow required the bump-commit author to
run `git tag` + `git push` manually; this collapses both into a single
explicit command without bundling bump + commit + tag (each stays its
own step per COR-004's anchoring principle).

Rollback (`unbump_version`, `untag_version`) is the symmetric inverse:
`untag` removes the local (and optionally remote) tag; `unbump`
narrows back the broadened `requires_backbone` upper bounds and
rewrites VERSION to the prior segment value. The pair only handles
strict-semver versions — pre-release suffixes are refused with a
clear message asking the user to set VERSION by hand, since the
prior version is ambiguous (was it the matching stable or the
previous pre-counter?).

`bump_version` also accepts an optional `--pre <kind>` to produce a
PEP 440 pre-release suffix (`X.Y.0rc1`, etc.); `bump_pre` increments
the counter on an existing suffix; `promote_version` drops the
suffix. Pre-release bumps do NOT broaden `requires_backbone` (per
the bump-policy: pre-releases are not a stable compatibility target).

The `requires_backbone` rewrite uses regex (not ruamel.yaml round-trip)
to preserve quoting style, indentation, and trailing comments.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Literal

import click

Segment = Literal["patch", "minor", "major"]
PreKind = Literal["a", "b", "rc"]

# Strict semver: major.minor.patch with no suffix. Used for operations
# that should refuse pre-release versions (e.g., `unbump`, `promote`'s
# input gate is the inverse — it requires a suffix).
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# PEP 440-aware: optional pre-release suffix `(a|b|rc)<N>` directly
# appended (no separator) per PEP 440's normal form for pre-releases.
# Captures: major, minor, patch, kind (or empty), counter (or empty).
_PEP440_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")

_REQUIRES_BACKBONE_RE = re.compile(r'(requires_backbone:\s*"[^"]*,<)(\d+)\.(\d+)\.(\d+)')


def _apply_segment(major: int, minor: int, patch: int, segment: Segment) -> tuple[int, int, int]:
    """Apply a semver `segment` bump to a `(major, minor, patch)` trio.

    Per PRJ-002: `major` resets minor+patch to 0 (the 0.x -> 1.0.0
    milestone and post-1.0 spec breakage both go through here); `minor`
    resets patch to 0; `patch` increments patch. Pure — the single place
    the segment arithmetic lives, shared by `bump_version` (which also
    writes) and `next_version` (which only computes).
    """
    if segment == "major":
        return major + 1, 0, 0
    if segment == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1  # patch


def next_version(current: str, segment: Segment) -> str:
    """Compute the next version string for `segment` from `current`.

    Pure — writes nothing, broadens nothing. Strips any pre-release
    suffix before computing (a segment bump leaves the pre-release line,
    mirroring `bump_version`). Raises `click.ClickException` on
    non-PEP-440 input. Used by the release step (per PRJ-002 D3) to
    compute each tier's new version from the current state on `main`.
    """
    match = _PEP440_RE.match(current)
    if match is None:
        raise click.ClickException(
            f"version {current!r} is not valid PEP 440 (expected major.minor.patch[(a|b|rc)N])"
        )
    major, minor, patch = (int(g) for g in match.group(1, 2, 3))
    major, minor, patch = _apply_segment(major, minor, patch, segment)
    return f"{major}.{minor}.{patch}"


def bump_version(source_kit: Path, segment: Segment, pre: PreKind | None = None) -> tuple[str, str]:
    """Bump `.pkit/VERSION` and broaden kit-shipped components' requires_backbone.

    With `pre`, appends a PEP 440 pre-release suffix (`X.Y.Z<kind>1`)
    and skips the broaden step (pre-releases are not a stable
    compatibility target — broadening waits for a later stable bump).

    Returns `(old_version, new_version)`.
    """
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        raise click.ClickException(f"source kit has no VERSION file at {version_file}")

    current = version_file.read_text(encoding="utf-8").strip()
    # The current VERSION may already carry a pre-release suffix (e.g.
    # `bump minor --pre rc` was previously run, and now the user is
    # bumping again). We strip the suffix to compute the segment bump;
    # PRE_RE captures both the strict trio and the suffixed form.
    match = _PEP440_RE.match(current)
    if match is None:
        raise click.ClickException(
            f"current version {current!r} is not valid PEP 440 "
            f"(expected major.minor.patch[(a|b|rc)N])"
        )

    major, minor, patch = (int(g) for g in match.group(1, 2, 3))
    major, minor, patch = _apply_segment(major, minor, patch, segment)

    new_version = f"{major}.{minor}.{patch}"
    if pre is not None:
        new_version = f"{new_version}{pre}1"

    version_file.write_text(f"{new_version}\n", encoding="utf-8")
    click.echo(f"Bumped backbone: {current} -> {new_version}")

    # Pre-release bumps don't broaden — pre-releases aren't a stable
    # target; the broaden waits for the matching stable promote/bump.
    if pre is None:
        _broaden_kit_components_requires_backbone(source_kit, major, minor)

    return current, new_version


def bump_pre(source_kit: Path) -> tuple[str, str]:
    """Increment the pre-release counter on the current VERSION.

    `1.2.0rc1` -> `1.2.0rc2`. Refuses if VERSION has no pre-release
    suffix. Does NOT broaden — see the rationale on `bump_version`.

    Returns `(old_version, new_version)`.
    """
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        raise click.ClickException(f"source kit has no VERSION file at {version_file}")

    current = version_file.read_text(encoding="utf-8").strip()
    match = _PEP440_RE.match(current)
    if match is None:
        raise click.ClickException(
            f"current version {current!r} is not valid PEP 440 "
            f"(expected major.minor.patch[(a|b|rc)N])"
        )

    kind = match.group(4)
    counter = match.group(5)
    if kind is None or counter is None:
        raise click.ClickException(
            f"current version {current!r} has no pre-release suffix to increment. "
            f"Use `pkit version bump <segment> --pre <kind>` to start a pre-release line."
        )

    new_counter = int(counter) + 1
    major, minor, patch = match.group(1, 2, 3)
    new_version = f"{major}.{minor}.{patch}{kind}{new_counter}"

    version_file.write_text(f"{new_version}\n", encoding="utf-8")
    click.echo(f"Bumped pre-release counter: {current} -> {new_version}")

    return current, new_version


def promote_version(source_kit: Path) -> tuple[str, str]:
    """Drop the pre-release suffix from VERSION.

    `1.2.0rc3` -> `1.2.0`. Refuses if no pre-release suffix is
    present. Does NOT broaden (kept symmetric with `bump --pre`; the
    broaden gate is `bump <segment>` without `--pre`).

    Returns `(old_version, new_version)`.
    """
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        raise click.ClickException(f"source kit has no VERSION file at {version_file}")

    current = version_file.read_text(encoding="utf-8").strip()
    match = _PEP440_RE.match(current)
    if match is None:
        raise click.ClickException(
            f"current version {current!r} is not valid PEP 440 "
            f"(expected major.minor.patch[(a|b|rc)N])"
        )

    kind = match.group(4)
    if kind is None:
        raise click.ClickException(
            f"current version {current!r} has no pre-release suffix to drop. "
            f"`promote` is a no-op on already-stable versions."
        )

    major, minor, patch = match.group(1, 2, 3)
    new_version = f"{major}.{minor}.{patch}"

    version_file.write_text(f"{new_version}\n", encoding="utf-8")
    click.echo(f"Promoted to stable: {current} -> {new_version}")

    return current, new_version


def unbump_version(source_kit: Path) -> tuple[str, str]:
    """Revert the most recent `bump <segment>` (without `--pre`).

    Narrows back `requires_backbone` upper bounds where the bump
    broadened them, then rewrites VERSION to the prior segment value
    (`1.2.0` -> `1.1.0`, `1.2.3` -> `1.2.2`).

    Refuses if:
    - the tag `v<current>` still exists locally (ordering: untag first),
    - the current VERSION carries a pre-release suffix (ambiguous),
    - the decrement would go pre-1.0 or is otherwise unclear (set
      VERSION by hand).

    Returns `(old_version, new_version)`.
    """
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        raise click.ClickException(f"source kit has no VERSION file at {version_file}")

    current = version_file.read_text(encoding="utf-8").strip()
    match = _SEMVER_RE.match(current)
    if match is None:
        raise click.ClickException(
            f"current version {current!r} is not strict semver. "
            f"`unbump` only handles X.Y.Z stable versions — set VERSION by hand "
            f"to roll back from a pre-release or non-semver value."
        )

    # Ordering: refuse if the tag for the current VERSION still exists.
    # The untag step must precede unbump so the tag never points at a
    # commit whose VERSION no longer matches.
    source_repo = source_kit.parent
    tag = f"v{current}"
    if _tag_exists_locally(source_repo, tag):
        raise click.ClickException(
            f"tag {tag} still exists locally. Run `pkit version untag` first "
            f"(then re-run `pkit version unbump`)."
        )

    major, minor, patch = (int(g) for g in match.groups())

    # Decrement rule per the spec:
    # - patch > 0 → patch -= 1 (1.2.3 → 1.2.2)
    # - patch == 0, minor > 0 → minor -= 1, patch = 0 (1.2.0 → 1.1.0)
    # - patch == 0, minor == 0 → unclear (would cross a major boundary
    #   or go pre-1.0); refuse.
    if patch > 0:
        new_major, new_minor, new_patch = major, minor, patch - 1
    elif minor > 0:
        new_major, new_minor, new_patch = major, minor - 1, 0
    else:
        raise click.ClickException(
            f"cannot determine prior version for {current!r} — "
            f"unbumping across a major boundary or pre-1.0 is ambiguous. "
            f"Set VERSION by hand."
        )

    new_version = f"{new_major}.{new_minor}.{new_patch}"

    # Narrow first (so the broaden-undo output is grouped with the
    # version-line output, matching the forward `bump` ordering).
    _narrow_kit_components_requires_backbone(source_kit, major, minor, new_major, new_minor)

    version_file.write_text(f"{new_version}\n", encoding="utf-8")
    click.echo(f"Unbumped backbone: {current} -> {new_version}")

    return current, new_version


def untag_version(source_kit: Path, push: bool = False) -> str:
    """Remove the local `v<version>` tag matching `.pkit/VERSION`.

    With `push=True`, also runs `git push origin :refs/tags/<tag>`
    to delete the remote tag. Refuses if the tag does not exist
    locally. Without `--push`, prints a hint with the exact
    remote-delete command.

    Returns the tag name (e.g., `v1.0.0`).
    """
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        raise click.ClickException(f"source kit has no VERSION file at {version_file}")

    version = version_file.read_text(encoding="utf-8").strip()
    # Accept pre-release versions here — `v1.2.0rc1` is a legitimate
    # tag form per the issue; the strict-semver gate is only on the
    # unbump path (where decrementing a pre-release is ambiguous).
    if not _PEP440_RE.match(version):
        raise click.ClickException(f"version {version!r} in {version_file} is not valid PEP 440")

    tag = f"v{version}"
    source_repo = source_kit.parent

    if not _tag_exists_locally(source_repo, tag):
        raise click.ClickException(f"tag {tag} does not exist locally — nothing to untag.")

    subprocess.run(
        ["git", "tag", "-d", tag],
        cwd=source_repo,
        check=True,
    )
    click.echo(f"Deleted local tag {tag}")

    if push:
        subprocess.run(
            ["git", "push", "origin", f":refs/tags/{tag}"],
            cwd=source_repo,
            check=True,
        )
        click.echo(f"Deleted remote tag {tag} on origin")
    else:
        click.echo(f"  hint: also remove the remote tag with `git push origin :refs/tags/{tag}`")

    return tag


def _broaden_kit_components_requires_backbone(
    source_kit: Path, new_major: int, new_minor: int
) -> None:
    """Walk every kit-shipped package.yaml and broaden the upper bound where needed.

    Mirrors the bash `broaden_kit_components_requires_backbone` helper.
    """
    new_upper = f"{new_major}.{new_minor + 1}.0"

    found_any = False
    for pkg_file in sorted(source_kit.rglob("package.yaml")):
        if not pkg_file.is_file():
            continue
        found_any = True
        rel_path = pkg_file.relative_to(source_kit)

        original = pkg_file.read_text(encoding="utf-8")
        match = _REQUIRES_BACKBONE_RE.search(original)
        if match is None:
            # Skipped silently if no requires_backbone field, with a
            # notice if the field exists but has no parseable upper
            # bound (e.g., `*`).
            if "requires_backbone:" in original:
                click.echo(
                    f"  skipped {rel_path} — requires_backbone has no parseable "
                    f"upper bound (consider updating manually)"
                )
            continue

        upper_major = int(match.group(2))
        upper_minor = int(match.group(3))

        # Broaden if new (major, minor) >= existing upper (major, minor).
        if new_major > upper_major or (new_major == upper_major and new_minor >= upper_minor):
            updated = _REQUIRES_BACKBONE_RE.sub(rf"\g<1>{new_upper}", original, count=1)
            pkg_file.write_text(updated, encoding="utf-8")

            old_range = _extract_range(match.string, match.start())
            new_range = old_range.rsplit("<", 1)[0] + f'<{new_upper}"'
            click.echo(f"  broadened {rel_path}: {old_range} -> {new_range}")

    if not found_any:
        click.echo("  (no kit-shipped package.yaml files found — nothing to broaden)")


def _narrow_kit_components_requires_backbone(
    source_kit: Path, old_major: int, old_minor: int, new_major: int, new_minor: int
) -> None:
    """Symmetric inverse of broaden: walk every kit-shipped package.yaml
    and narrow the upper bound back where the broadening was driven by
    the now-removed version.

    Only narrows entries whose current upper bound exactly equals the
    one the previous broaden would have written (`old_major.(old_minor+1).0`).
    That bound is rewritten to `new_major.(new_minor+1).0`. Components
    whose range was already broader (e.g., set manually wider) or already
    narrower (broaden was a no-op for them) are left alone.
    """
    broadened_upper = f"{old_major}.{old_minor + 1}.0"
    new_upper = f"{new_major}.{new_minor + 1}.0"

    found_any = False
    for pkg_file in sorted(source_kit.rglob("package.yaml")):
        if not pkg_file.is_file():
            continue
        found_any = True
        rel_path = pkg_file.relative_to(source_kit)

        original = pkg_file.read_text(encoding="utf-8")
        match = _REQUIRES_BACKBONE_RE.search(original)
        if match is None:
            continue

        upper = f"{match.group(2)}.{match.group(3)}.{match.group(4)}"
        if upper != broadened_upper:
            # Not a broaden we did, or already-wider/narrower; skip.
            continue

        updated = _REQUIRES_BACKBONE_RE.sub(rf"\g<1>{new_upper}", original, count=1)
        pkg_file.write_text(updated, encoding="utf-8")

        old_range = _extract_range(match.string, match.start())
        new_range = old_range.rsplit("<", 1)[0] + f'<{new_upper}"'
        click.echo(f"  narrowed {rel_path}: {old_range} -> {new_range}")

    if not found_any:
        click.echo("  (no kit-shipped package.yaml files found — nothing to narrow)")


def _extract_range(text: str, match_start: int) -> str:
    """Extract the full `"...,<X.Y.Z"` quoted range starting at `match_start`.

    `match_start` is the position of "r" in "requires_backbone:". The
    opening quote of the range comes AFTER that (after the colon and
    whitespace); the closing quote is the next `"` after the opening.
    """
    quote_start = text.find('"', match_start)
    quote_end = text.find('"', quote_start + 1) + 1
    return text[quote_start:quote_end]


def tag_version(source_kit: Path, push: bool = False) -> str:
    """Tag HEAD as `v<version>` where `<version>` is read from `.pkit/VERSION`.

    Returns the tag name (e.g., `v1.0.0`). Raises `click.ClickException`
    on any precondition failure (missing VERSION, invalid version, tag
    already exists, not in a git repo). When `push=True`, also pushes
    the tag to `origin`.

    The annotation message is `"v<version>"` plus the body of the most
    recent commit (so the tag carries a hint of what the bump was for).

    Accepts pre-release versions (`v1.2.0rc1`); the tag form stays
    `v<version>` literally per PRJ-004.
    """
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        raise click.ClickException(f"source kit has no VERSION file at {version_file}")

    version = version_file.read_text(encoding="utf-8").strip()
    if not _PEP440_RE.match(version):
        raise click.ClickException(f"version {version!r} in {version_file} is not valid PEP 440")

    tag = f"v{version}"
    source_repo = source_kit.parent

    # Refuse if the tag already exists (locally or on origin).
    if _tag_exists_locally(source_repo, tag):
        raise click.ClickException(
            f"tag {tag} already exists locally. Delete it first with "
            f"`git tag -d {tag}` if you intend to retag, or bump the version."
        )

    # Build the annotation: the bump commit's subject line, or just the
    # version if `git log` fails for any reason.
    commit_subject = _last_commit_subject(source_repo)
    annotation = f"{tag}"
    if commit_subject:
        annotation += f"\n\n{commit_subject}"

    subprocess.run(
        ["git", "tag", "-a", tag, "-m", annotation],
        cwd=source_repo,
        check=True,
    )
    click.echo(f"Tagged HEAD as {tag}")

    if push:
        subprocess.run(
            ["git", "push", "origin", tag],
            cwd=source_repo,
            check=True,
        )
        click.echo(f"Pushed {tag} to origin")

    return tag


def _tag_exists_locally(source_repo: Path, tag: str) -> bool:
    """Return True if `tag` exists in the local git repo at `source_repo`."""
    result = subprocess.run(
        ["git", "tag", "-l", tag],
        capture_output=True,
        text=True,
        cwd=source_repo,
        check=True,
    )
    return result.stdout.strip() == tag


def _last_commit_subject(source_repo: Path) -> str:
    """Return the most recent commit's subject line, or '' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            capture_output=True,
            text=True,
            cwd=source_repo,
            check=False,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
