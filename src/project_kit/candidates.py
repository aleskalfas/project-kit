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
  (`refuse_no_pin`).
- **The first hop,** from a final release whose pkit has no `--pre`, is the
  candidate's own upgrade, run through the router's bypass (`first_hop`;
  ADR-089 point 8).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import click
from packaging.version import InvalidVersion, Version

from project_kit.install import LATEST_TAG
from project_kit.migrations import public_version
from project_kit.router import DISTRIBUTION_GIT_URL

# A candidate in PEP 440's normal form: `X.Y.ZrcN`, no part padded by a leading
# zero, as the release step writes it and its tag carries it (PRJ-004).
_CANDIDATE_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)rc(0|[1-9]\d*)$")


def is_candidate(version: str | None) -> bool:
    """Whether *version* names a release candidate in PEP 440's normal form,
    `X.Y.ZrcN`: the only spelling the router can route to the candidate's tag,
    which it reaches as `v<version>` (ADR-089 point 6)."""
    return version is not None and _CANDIDATE_RE.match(version) is not None


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
