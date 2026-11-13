"""A release candidate as a project meets it (ADR-089 points 6 to 8, as ADR-092 refines them).

A release candidate is a set of versions cut to test changes before they ship,
each one it raises suffixed `rcN` (PRJ-016 point 3). A project moves onto one
only when someone asks, and such a move always pins (ADR-089 point 7):

- **A pin may name one,** in PEP 440's normal form, `X.Y.ZrcN`, the form the
  candidate's tag `vX.Y.ZrcN` carries (`is_candidate`; ADR-089 point 6).
- **An upgrade or an `init` refuses one nobody asked for** (`refuse_unasked`,
  `refuse_init`). Someone asks by `pkit upgrade --pre`, by a run with routing
  bypassed, or by a pin that names the candidate.
- **A move to one always pins,** so `--no-pin` is refused on it
  (`refuse_no_pin`), and `pkit unpin` refuses in a project on one
  (`refuse_unpin`).
- **The first hop,** from a final release whose pkit has no `--pre`, is the
  candidate's own upgrade, run through the router's bypass (`first_hop`;
  ADR-089 point 8).

A project on a candidate moves to no other release, and leaves it only by the
ways off PRJ-016 point 4 sets (`ways_off`):

- **No move off it.** An upgrade or a raise of the pin refuses to move a project
  whose manifest records a candidate (`recorded_candidate`) to any release but
  that candidate (`refuse_move_off`; ADR-092 point 7).
- **No entry from above its base.** A candidate's own upgrade refuses a window
  that starts above the versions its cut was made from, which its own package
  records (`refuse_above_base`; ADR-092 point 9).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import click
from packaging.version import InvalidVersion, Version

from project_kit.install import LATEST_TAG
from project_kit.manifest import BackboneManifest
from project_kit.migrations import public_version
from project_kit.router import DISTRIBUTION_GIT_URL
from project_kit.versioning import is_candidate_version


def is_candidate(version: str | None) -> bool:
    """Whether *version* names a release candidate in PEP 440's normal form,
    `X.Y.ZrcN`: the only spelling the router can route to the candidate's tag,
    which it reaches as `v<version>` (ADR-089 point 6)."""
    return version is not None and is_candidate_version(version)


def normal_form(token: str) -> str | None:
    """*token* as PEP 440's normal form writes it, or None when it is no version.
    So `2.0.0-rc.1` and `2.0.0RC1` both read as `2.0.0rc1`."""
    try:
        return str(Version(token))
    except InvalidVersion:
        return None


def first_hop(candidate: str) -> str:
    """The way into *candidate* from a final release whose pkit has no `--pre`: the
    candidate's own upgrade, run through the router's bypass, fetched from the
    distribution URL compiled into the tool at the candidate's tag (ADR-089 point
    8). Typing the bypass is the operator's consent."""
    return f"PKIT_NO_ROUTE=1 uvx --from {DISTRIBUTION_GIT_URL}@v{candidate} project-kit upgrade"


def latest_tool_install() -> str:
    """The install that puts the highest final release back as the machine's tool,
    over whatever release the tool is at (PRJ-004)."""
    return f"uv tool install --force {DISTRIBUTION_GIT_URL}@{LATEST_TAG}"


def refuse_unasked(
    target: str,
    *,
    pre: bool,
    bypassed: bool,
    pin: str | None,
    installed_tool: Callable[[], bool],
) -> None:
    """Refuse an upgrade whose *target* is a release candidate nobody asked for,
    before it writes anything (ADR-089 point 7).

    Someone asked where `--pre` was passed (*pre*), where routing is *bypassed*,
    as a raise and the first hop both run, or where the project's *pin* names
    the candidate. A target at a release version never meets the guard. The
    message names the ways in, and, where the running pkit is the installed
    tool, as *installed_tool* says, the install of the latest release: a
    candidate installed as the tool would otherwise meet the guard in every
    project it upgrades.
    """
    if not is_candidate(target) or pre or bypassed:
        return
    if pin is not None and public_version(pin) == public_version(target):
        return
    lines = [
        f"refusing to move this project to pkit {target}: it is a release candidate, and a "
        "project moves onto one only when someone asks (ADR-089 point 7). Nothing was written.",
        "To move it onto a candidate on purpose, run `pkit upgrade --pre`: it moves the "
        "project to the newest release, candidates included, and pins it there.",
        f"Or run this candidate's own upgrade through the router's bypass: `{first_hop(target)}`.",
    ]
    if installed_tool():
        lines.append(
            f"This pkit, {target}, is your installed tool. To install the latest release as "
            f"your tool instead, run `{latest_tool_install()}`, then `pkit upgrade` again."
        )
    raise click.ClickException("\n       ".join(lines))


def refuse_no_pin(target: str, *, pin: bool) -> None:
    """Refuse `--no-pin` on an upgrade whose *target* is a release candidate (*pin*
    False is the flag), before it writes anything (ADR-089 point 7, ADR-064 point
    2). A move to a candidate always pins, so the router keeps the project on the
    candidate's code whatever tool is installed."""
    if pin or not is_candidate(target):
        return
    raise click.ClickException(
        f"refusing `--no-pin`: this upgrade's target is pkit {target}, a release candidate. "
        "A move to a candidate always pins, so that the project keeps running the "
        "candidate's code whatever pkit is installed (ADR-089 point 7). Nothing was "
        "written. Run it again without `--no-pin`."
    )


def refuse_init(version: str, target_root: Path, *, bypassed: bool) -> None:
    """Refuse an `init` run by *version*, a release candidate, unless routing is
    *bypassed*, before it writes anything (ADR-089 point 7, ADR-064 point 3). A
    candidate installed as the machine's tool would otherwise install each new
    project at a candidate. An `init` let through pins the project it installs
    (`install.install_kit`)."""
    if not is_candidate(version) or bypassed:
        return
    raise click.ClickException(
        "\n       ".join(
            [
                f"refusing to install pkit {version} into {target_root}: it is a release "
                "candidate, and a project moves onto one only when someone asks (ADR-089 "
                "point 7). Nothing was written.",
                "To install it on purpose, run the same command again with routing "
                f"bypassed, as `PKIT_NO_ROUTE=1 pkit init`. The install then pins the project "
                f"at {version}.",
                f"To install the latest release instead, run `{latest_tool_install()}`, then "
                "`pkit init` again.",
            ]
        )
    )


# --- A project on a candidate (ADR-092 points 7 and 9) ---------------------------


def recorded_candidate(manifest: BackboneManifest | None) -> str | None:
    """The release candidate *manifest* records: its target, `backbone_version`,
    where that is a candidate, else its completion, `completed_version`, where
    that is one. None where it records no candidate, or there is no manifest."""
    if manifest is None:
        return None
    for version in (manifest.backbone_version, manifest.completed_version):
        if is_candidate(version):
            return version
    return None


def ways_off(candidate: str) -> list[str]:
    """The ways off *candidate* PRJ-016 point 4 sets, as each refusal of a move off
    it names them: the project leaves the testers' branch, and from the final
    release it stood at upgrades or enters a later candidate. A project the
    candidate's `init` installed starts again from a final release's `init`."""
    return [
        f"To leave {candidate}, leave the testers' branch, the branch of this project that "
        "entered it: switch back to a branch at the final release the project stood at. "
        "From there, `pkit upgrade` moves it on, or it enters a later candidate (PRJ-016 "
        "point 4).",
        f"A project that {candidate}'s `pkit init` installed has no such branch: install it "
        "again with a final release's `pkit init`.",
    ]


def refuse_move_off(manifest: BackboneManifest | None, target: str) -> None:
    """Refuse to move a project whose *manifest* records a release candidate to
    *target*, any release but that candidate, before anything is written (ADR-092
    point 7). Every upgrade, with `--pre` or without, and every raise of the pin
    calls it with the release its move would reach.

    The message names the ways off (`ways_off`), and, where the move to the
    candidate was cut short, `pkit upgrade --pre`, which targets the recorded
    candidate and so only finishes that move.
    """
    candidate = recorded_candidate(manifest)
    if manifest is None or candidate is None:
        return
    if public_version(target) == public_version(candidate):
        return
    lines = [
        f"refusing to move this project to pkit {target}: its manifest records the release "
        f"candidate {candidate}, and a project on a candidate moves to no other release, "
        "candidate or final (ADR-092 point 7). Nothing was written.",
    ]
    if manifest.backbone_version == candidate and manifest.transition_incomplete:
        lines.append(
            f"Its move to {candidate} was cut short: `pkit upgrade --pre` finishes it, and "
            "moves the project to no other release."
        )
    lines.extend(ways_off(candidate))
    raise click.ClickException("\n       ".join(lines))


def refuse_unpin(manifest: BackboneManifest | None) -> None:
    """Refuse `pkit unpin` in a project whose *manifest* records a release
    candidate, before anything is written (ADR-089 point 7). A project on a
    candidate stays pinned, so the router keeps running the candidate's code
    whatever pkit is installed. The message names the ways off (`ways_off`)."""
    candidate = recorded_candidate(manifest)
    if candidate is None:
        return
    raise click.ClickException(
        "\n       ".join(
            [
                "refusing to remove this project's pin: its manifest records the release "
                f"candidate {candidate}, and a project on a candidate stays pinned, so that "
                "the router keeps running the candidate's code whatever pkit is installed "
                "(ADR-089 point 7). Nothing was written.",
                *ways_off(candidate),
            ]
        )
    )


def own_base_file() -> Path:
    """Where this pkit's own package keeps its cut's base, which a release
    candidate's package alone carries (ADR-092 point 9)."""
    from project_kit.release_candidate import BASE_PATH

    return Path(__file__).parent / BASE_PATH.name


def refuse_above_base(
    candidate: str, *, backbone_from: str | None, components_from: Mapping[str, str]
) -> None:
    """In a release candidate's own upgrade, refuse a migration window that starts
    above its cut's base, before anything is written (ADR-092 point 9).

    *candidate* is the version the running pkit's bundle records: an upgrade by a
    final release meets no such refusal. The base, the version the backbone and
    each component recorded at the commit the candidate was cut from, is read
    from the candidate's own package (`own_base_file`), and a base it cannot read
    refuses too, since the limit could not be kept. *backbone_from* is where the
    backbone's window starts, None where it runs none or runs from no completion,
    and *components_from* where each moving component's starts, by name. A window
    that starts above the version the base records for its component would pass
    over what a final release made after the cut ran. The message names entering
    from a final release at or below the base, or waiting for the next cut.
    """
    if not is_candidate(candidate):
        return
    from project_kit.release_candidate import parse_base

    path = own_base_file()
    try:
        base = parse_base(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise click.ClickException(
            "\n       ".join(
                [
                    f"refusing to move this project to pkit {candidate}: this release "
                    "candidate carries no readable record of the versions it was cut from "
                    f"({path.name}: {exc}), so it cannot tell whether this project may "
                    "enter it (ADR-092 point 9). Nothing was written.",
                    "A candidate run from its tag carries that record: run its own upgrade "
                    f"from the tag, `{first_hop(candidate)}`.",
                ]
            )
        ) from None
    above: list[str] = []
    if backbone_from is not None and _above(backbone_from, base.backbone):
        above.append(f"the backbone's from {backbone_from}, above {base.backbone}")
    for name, start in sorted(components_from.items()):
        recorded = base.components.get(name)
        if recorded is not None and _above(start, recorded):
            above.append(f"{name}'s from {start}, above {recorded}")
    if not above:
        return
    raise click.ClickException(
        "\n       ".join(
            [
                f"refusing to move this project to pkit {candidate}: the migrations it would "
                "run here start above the versions it was cut from, so they would pass over "
                "what a final release made after the cut ran in this project (ADR-092 point "
                "9). Nothing was written.",
                "The windows that start above the cut: " + "; ".join(above) + ".",
                f"Enter {candidate} from a final release at or below the versions it was cut "
                f"from, pkit {base.backbone} for the backbone, or wait for the next candidate, "
                "cut once its branch has taken in the release this project is at.",
            ]
        )
    )


def _above(version: str, ceiling: str) -> bool:
    """Whether *version* is newer than *ceiling*, both read as public versions, the
    pre-release kept; False where either is no version, so only an unambiguous
    order refuses."""
    parsed, parsed_ceiling = public_version(version), public_version(ceiling)
    return parsed is not None and parsed_ceiling is not None and parsed > parsed_ceiling
