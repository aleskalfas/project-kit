"""Tests for `project_kit.candidates`: a release candidate as a project meets it
(ADR-089 points 6 to 8, as ADR-092 refines them).

The upgrade's and the pin's uses of it are in `test_upgrade.py` and
`test_pin_cli.py`, and the `init`'s in `test_install.py`.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import candidates, router


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("2.0.0rc1", True),
        ("10.20.30rc0", True),
        ("2.0.0", False),
        ("2.0.0-rc.1", False),
        ("2.0.0RC1", False),
        ("2.0.0.rc1", False),
        ("02.0.0rc1", False),
        ("2.0.0rc01", False),
        ("2.0.0a1", False),
        ("2.0.0rc1.dev1", False),
        ("2.0.0rc1+local", False),
        ("v2.0.0rc1", False),
        (None, False),
    ],
)
def test_a_candidate_is_named_in_pep_440_normal_form_alone(
    version: str | None, expected: bool
) -> None:
    """Only `X.Y.ZrcN`, no part padded, names a candidate: the form its tag carries,
    which the router reaches as `v<version>` (ADR-089 point 6)."""
    assert candidates.is_candidate(version) is expected


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("2.0.0-rc.1", "2.0.0rc1"),
        ("2.0.0RC1", "2.0.0rc1"),
        ("2.0.0.rc1", "2.0.0rc1"),
        ("2.0.0rc1", "2.0.0rc1"),
        ("feature-branch", None),
    ],
)
def test_normal_form_reads_another_spelling_as_pep_440_writes_it(
    token: str, expected: str | None
) -> None:
    assert candidates.normal_form(token) == expected


def test_the_first_hop_is_the_candidates_own_upgrade_through_the_bypass() -> None:
    """The first hop fetches the candidate from the distribution URL at its tag, and
    runs its upgrade with routing bypassed (ADR-089 point 8)."""
    assert candidates.first_hop("3.0.0rc1") == (
        f"PKIT_NO_ROUTE=1 uvx --from {router.DISTRIBUTION_GIT_URL}@v3.0.0rc1 project-kit upgrade"
    )


@pytest.mark.parametrize(
    ("target", "pre", "pin", "bypassed"),
    [
        pytest.param("2.0.0", False, None, False, id="a-release"),
        pytest.param("2.0.0rc1", True, None, False, id="pre"),
        pytest.param("2.0.0rc1", False, None, True, id="bypassed"),
        pytest.param("2.0.0rc1", False, "2.0.0rc1", False, id="a-pin-that-names-it"),
    ],
)
def test_the_guard_lets_a_release_and_each_way_in_through(
    target: str, pre: bool, pin: str | None, bypassed: bool
) -> None:
    """A release never meets the guard. A candidate passes where someone asked: by
    `--pre`, a run with routing bypassed, or a pin that names it (ADR-089 point 7)."""
    candidates.refuse_unasked(
        target, pre=pre, bypassed=bypassed, pin=pin, installed_tool=lambda: True
    )


@pytest.mark.parametrize("pin", [None, "1.9.0", "2.0.0rc2"])
def test_the_guard_refuses_a_candidate_its_pin_does_not_name(pin: str | None) -> None:
    """A pin at another version asks for no candidate, nor does one that names
    another candidate (ADR-089 point 7)."""
    with pytest.raises(click.ClickException, match="refusing to move this project to pkit"):
        candidates.refuse_unasked(
            "2.0.0rc1", pre=False, bypassed=False, pin=pin, installed_tool=lambda: False
        )


@pytest.mark.parametrize(
    ("target", "pin", "refused"),
    [
        ("2.0.0rc1", False, True),
        ("2.0.0rc1", True, False),
        ("2.0.0", False, False),
    ],
)
def test_no_pin_is_refused_on_a_move_to_a_candidate_alone(
    target: str, pin: bool, refused: bool
) -> None:
    """A move to a candidate always pins; a move to a release may stay unpinned
    (ADR-089 point 7, ADR-064 point 2)."""
    if refused:
        with pytest.raises(click.ClickException, match="refusing `--no-pin`"):
            candidates.refuse_no_pin(target, pin=pin)
    else:
        candidates.refuse_no_pin(target, pin=pin)


def test_an_init_by_a_candidate_refuses_unless_routing_is_bypassed(tmp_path: Path) -> None:
    """An `init` run by a candidate refuses, and names the bypass and the install of
    the latest release; with routing bypassed it passes, as an `init` by a release
    always does (ADR-089 point 7)."""
    with pytest.raises(click.ClickException) as excinfo:
        candidates.refuse_init("2.0.0rc1", tmp_path, bypassed=False)
    message = " ".join(excinfo.value.message.split())
    assert f"refusing to install pkit 2.0.0rc1 into {tmp_path}" in message
    assert "`PKIT_NO_ROUTE=1 pkit init`" in message
    assert f"`uv tool install --force {router.DISTRIBUTION_GIT_URL}@latest`" in message

    candidates.refuse_init("2.0.0", tmp_path, bypassed=False)
    candidates.refuse_init("2.0.0rc1", tmp_path, bypassed=True)
