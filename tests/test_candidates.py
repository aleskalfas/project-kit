"""Tests for `project_kit.candidates`: a release candidate as a project meets it
(ADR-089 points 6 to 8, as ADR-092 refines them, and ADR-092 points 7 and 9).

The upgrade's and the pin's uses of it are in `test_upgrade.py` and
`test_pin_cli.py`, and the `init`'s in `test_install.py`.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import candidates, router
from project_kit.manifest import BackboneManifest
from project_kit.release_candidate import Base


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


# --- A project on a candidate (ADR-092 points 7 and 9) ---------------------------


def _manifest(backbone: str, completed: str | None) -> BackboneManifest:
    return BackboneManifest(backbone_version=backbone, completed_version=completed)


def _one_line(message: str) -> str:
    return " ".join(message.split())


@pytest.mark.parametrize(
    ("backbone", "completed", "expected"),
    [
        pytest.param("2.0.0rc1", "2.0.0rc1", "2.0.0rc1", id="on-it"),
        pytest.param("2.0.0rc1", "1.9.0", "2.0.0rc1", id="a-move-onto-it-cut-short"),
        pytest.param("2.0.0rc1", None, "2.0.0rc1", id="no-completion"),
        pytest.param("2.0.0", "2.0.0rc1", "2.0.0rc1", id="only-its-completion"),
        pytest.param("2.0.0", "2.0.0", None, id="a-final-release"),
    ],
)
def test_the_candidate_a_manifest_records_is_its_target_else_its_completion(
    backbone: str, completed: str | None, expected: str | None
) -> None:
    assert candidates.recorded_candidate(_manifest(backbone, completed)) == expected


def test_no_manifest_records_no_candidate() -> None:
    assert candidates.recorded_candidate(None) is None


@pytest.mark.parametrize(
    "manifest",
    [
        pytest.param(None, id="no-manifest"),
        pytest.param(_manifest("2.0.0", "2.0.0"), id="a-final-release"),
        pytest.param(_manifest("2.0.0rc1", "2.0.0rc1"), id="to-the-candidate-itself"),
        pytest.param(_manifest("2.0.0rc1", "1.9.0"), id="finishing-a-move-cut-short"),
    ],
)
def test_a_move_to_the_recorded_candidate_or_from_a_final_release_passes(
    manifest: BackboneManifest | None,
) -> None:
    """Only a project whose manifest records a candidate is held, and a move to that
    candidate is no move off it (ADR-092 point 7)."""
    candidates.refuse_move_off(manifest, "2.0.0rc1")


@pytest.mark.parametrize("target", ["2.0.0", "2.0.0rc2", "2.1.0", "1.9.1"])
def test_a_move_off_the_recorded_candidate_refuses_and_names_the_ways_off(target: str) -> None:
    """A project on a candidate moves to no other release, candidate or final, and
    the message names PRJ-016 point 4's ways off (ADR-092 point 7)."""
    with pytest.raises(click.ClickException) as excinfo:
        candidates.refuse_move_off(_manifest("2.0.0rc1", "2.0.0rc1"), target)

    message = _one_line(excinfo.value.message)
    assert (
        f"refusing to move this project to pkit {target}: its manifest records the release "
        "candidate 2.0.0rc1, and a project on a candidate moves to no other release"
    ) in message
    assert "Nothing was written" in message
    assert "leave the testers' branch" in message
    assert "`pkit upgrade` moves it on, or it enters a later candidate (PRJ-016 point 4)" in (
        message
    )
    assert "install it again with a final release's `pkit init`" in message
    assert "cut short" not in message


def test_a_move_off_a_candidate_whose_move_was_cut_short_names_pre() -> None:
    """Where the move onto the candidate was cut short, the refusal also names `pkit
    upgrade --pre`, which finishes that move and takes no other release (ADR-092
    point 7)."""
    with pytest.raises(click.ClickException) as excinfo:
        candidates.refuse_move_off(_manifest("2.0.0rc1", "1.9.0"), "2.0.0")

    assert (
        "Its move to 2.0.0rc1 was cut short: `pkit upgrade --pre` finishes it, and moves the "
        "project to no other release."
    ) in _one_line(excinfo.value.message)


def test_unpin_refuses_in_a_project_on_a_candidate_alone() -> None:
    """A project on a candidate stays pinned, and the refusal names the ways off
    (ADR-089 point 7, PRJ-016 point 4)."""
    candidates.refuse_unpin(None)
    candidates.refuse_unpin(_manifest("2.0.0", "2.0.0"))

    with pytest.raises(click.ClickException) as excinfo:
        candidates.refuse_unpin(_manifest("2.0.0rc1", "1.9.0"))

    message = _one_line(excinfo.value.message)
    assert (
        "refusing to remove this project's pin: its manifest records the release candidate 2.0.0rc1"
    ) in message
    assert "Nothing was written" in message
    assert "leave the testers' branch" in message


def _cut(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, base: Base) -> None:
    """Make *base* the cut's base the running candidate's own package records."""
    where = tmp_path / "candidate_base.json"
    where.write_text(base.text(), encoding="utf-8")
    monkeypatch.setattr(candidates, "own_base_file", lambda: where)


_BASE = Base("0" * 40, "2.1.0", {"claude-code": "1.4.0", "project-management": "0.30.0"})


@pytest.mark.parametrize(
    ("backbone_from", "components_from"),
    [
        pytest.param(None, {}, id="no-window"),
        pytest.param("2.1.0", {}, id="at-the-base"),
        pytest.param("2.0.0", {"claude-code": "1.3.0"}, id="below-the-base"),
        pytest.param(None, {"claude-code": "1.4.0"}, id="a-component-at-the-base"),
        pytest.param(None, {"a-component-of-its-own": "9.0.0"}, id="no-version-in-the-base"),
    ],
)
def test_a_window_at_or_below_the_base_passes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backbone_from: str | None,
    components_from: dict[str, str],
) -> None:
    """A window that starts at or below the version the base records for its
    component passes (ADR-092 point 9)."""
    _cut(monkeypatch, tmp_path, _BASE)

    candidates.refuse_above_base(
        "3.0.0rc2", backbone_from=backbone_from, components_from=components_from
    )


def test_a_window_above_the_base_refuses_naming_each_and_the_ways_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A window that starts above the version the base records refuses, for the
    backbone and for a component alike, and the message names entering from a final
    release at or below the base, or waiting for the next cut (ADR-092 point 9)."""
    _cut(monkeypatch, tmp_path, _BASE)

    with pytest.raises(click.ClickException) as excinfo:
        candidates.refuse_above_base(
            "3.0.0rc2",
            backbone_from="2.2.0",
            components_from={"project-management": "0.31.0", "claude-code": "1.4.0"},
        )

    message = _one_line(excinfo.value.message)
    assert "refusing to move this project to pkit 3.0.0rc2" in message
    assert "Nothing was written" in message
    assert (
        "The windows that start above the cut: the backbone's from 2.2.0, above 2.1.0; "
        "project-management's from 0.31.0, above 0.30.0."
    ) in message
    assert "claude-code's" not in message
    assert "from a final release at or below the versions it was cut from, pkit 2.1.0" in message
    assert "or wait for the next candidate" in message


def test_an_upgrade_by_a_final_release_reads_no_base(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A final release carries no base, and its upgrade meets no such refusal."""
    monkeypatch.setattr(candidates, "own_base_file", lambda: tmp_path / "missing.json")

    candidates.refuse_above_base("3.0.0", backbone_from="9.0.0", components_from={})


@pytest.mark.parametrize("text", [None, "not json", '{"commit": "x"}'], ids=str)
def test_a_candidate_whose_base_cannot_be_read_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, text: str | None
) -> None:
    """A candidate that cannot read its base cannot keep the limit, so it refuses,
    and names the candidate's upgrade run from its tag (ADR-092 point 9)."""
    where = tmp_path / "candidate_base.json"
    if text is not None:
        where.write_text(text, encoding="utf-8")
    monkeypatch.setattr(candidates, "own_base_file", lambda: where)

    with pytest.raises(click.ClickException) as excinfo:
        candidates.refuse_above_base("3.0.0rc2", backbone_from=None, components_from={})

    message = _one_line(excinfo.value.message)
    assert "carries no readable record of the versions it was cut from" in message
    assert f"`{candidates.first_hop('3.0.0rc2')}`" in message


def test_the_base_is_read_from_the_candidates_own_package() -> None:
    """The base sits in the package beside this module, where the cut writes it and
    the wheel carries it (ADR-092 point 9)."""
    assert candidates.own_base_file() == Path(candidates.__file__).parent / "candidate_base.json"
