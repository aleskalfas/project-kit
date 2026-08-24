"""The prerequisite gate — unit behaviour of `_lib/bootstrap_gate` (#747).

The gate is what turns [project-management:DEC-017]'s documented "hard gate on
every pm operation" into code: before #747, no pm script called `pre-check`, and
`_lib.gh.load_adopter_config` handed every reader an empty dict for a missing
config, so an un-bootstrapped project was not refused — it silently got defaults
for the substrate map, the board flag, review mode, doc mappings and
workstreams.

What is pinned here (the decision surface, one test apiece):
  * a project with no stamp is refused, and the refusal NAMES the command that
    fixes it (the hint is the point — a self-remedying failure, not a puzzle);
  * a stamped project with a healthy config passes;
  * a stamped project whose config went missing / unparseable / short of a
    required key / carrying an unknown key is refused (a config can break
    AFTER a successful bootstrap — the stamp alone is not enough);
  * a stamp copied in from another repository is refused rather than honoured
    (the stamp lives in the seed-once `project/` subtree, so it travels);
  * an unresolvable repo identity does NOT fabricate a refusal;
  * staleness (stamp version != installed version) is REPORTED, never a
    refusal on its own;
  * the exemption list is exactly the five setup-and-diagnosis verbs;
  * a gate that cannot evaluate fails CLOSED.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"


@pytest.fixture(scope="module", autouse=True)
def _scripts_on_path():
    sys.path.insert(0, str(SCRIPTS))
    yield
    sys.path.remove(str(SCRIPTS))


@pytest.fixture(scope="module")
def gate(_scripts_on_path):
    from _lib import bootstrap_gate

    return bootstrap_gate


# --- fixtures: a capability tree in a temp repo ---------------------------


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _repo(tmp_path: Path, *, origin: str | None = None) -> Path:
    """A git repo, optionally with an `origin` remote."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    if origin is not None:
        _git(["remote", "add", "origin", origin], tmp_path)
    return tmp_path


def _capability_tree(root: Path, *, config: str | None = "valid") -> Path:
    """An installed capability tree: package.yaml + config schema + config.

    `config` selects the adopter config written: "valid" (the minimal accepted
    shape), None (no config file at all), or a raw string written verbatim.
    """
    cap = root / ".pkit" / "capabilities" / "project-management"
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "project").mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        "schema_version: 2\ncomponent:\n  kind: capability\n"
        "  name: project-management\n  version: 0.54.0\n",
        encoding="utf-8",
    )
    # The real companion schema — the gate derives its shape rules from it, so
    # the test must not hand it a stand-in.
    (cap / "schemas" / "config.schema.json").write_text(
        (CAPABILITY / "schemas" / "config.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if config == "valid":
        (cap / "project" / "config.yaml").write_text(
            "schema_version: 1\ndefault_branch: main\nworkstreams: []\n",
            encoding="utf-8",
        )
    elif config is not None:
        (cap / "project" / "config.yaml").write_text(config, encoding="utf-8")
    return cap


def _stamp(gate, cap: Path, **overrides: object) -> Path:
    """Write a stamp, optionally overriding fields inside the `bootstrap:` block."""
    from ruamel.yaml import YAML

    path = gate.write_stamp(cap, by=gate.BY_BOOTSTRAP)
    if overrides:
        yaml = YAML(typ="safe")
        data = yaml.load(path.read_text(encoding="utf-8"))
        data["bootstrap"].update(overrides)
        with path.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
    return path


# --- the missing-stamp refusal, and its hint -----------------------------


def test_unbootstrapped_project_is_refused(gate, tmp_path):
    """The headline case: a config-complete project that never bootstrapped is
    refused, not silently defaulted."""
    cap = _capability_tree(_repo(tmp_path / "repo"))
    outcome = gate.evaluate(cap)
    assert not outcome.ok
    assert "never completed `bootstrap`" in outcome.reason


def test_refusal_names_the_exact_command_to_run(gate, tmp_path):
    """The failure must be self-remedying: the message names the dispatcher
    form, the direct-script form, and pre-check for the full diagnosis — and
    names the verb the user actually typed."""
    cap = _capability_tree(_repo(tmp_path / "repo"))
    message = gate.refusal_message("move-issue", gate.evaluate(cap))
    assert "move-issue" in message
    assert "pkit project-management bootstrap" in message
    assert (
        "uv run --script .pkit/capabilities/project-management/scripts/bootstrap.py"
        in message
    )
    assert "pkit project-management pre-check" in message


def test_enforce_prints_the_refusal_and_returns_false(gate, tmp_path, capsys):
    cap = _capability_tree(_repo(tmp_path / "repo"))
    assert gate.enforce("show-issue", capability_root=cap) is False
    err = capsys.readouterr().err
    assert "[refused] show-issue" in err
    assert "pkit project-management bootstrap" in err


def test_missing_capability_is_refused_not_crashed(gate, tmp_path):
    """No capability tree at all → a refusal that says so, not a traceback."""
    outcome = gate.evaluate(tmp_path / "nowhere")
    assert not outcome.ok
    assert "not installed" in outcome.reason


# --- the bootstrapped project passes -------------------------------------


def test_bootstrapped_project_passes(gate, tmp_path):
    cap = _capability_tree(_repo(tmp_path / "repo", origin="git@github.com:acme/x.git"))
    _stamp(gate, cap)
    outcome = gate.evaluate(cap)
    assert outcome.ok, outcome.reason
    assert outcome.stamp is not None
    assert outcome.stamp.by == gate.BY_BOOTSTRAP


def test_written_stamp_matches_its_companion_schema(gate, tmp_path):
    """The writer's output is a valid instance of the shipped schema — so
    `pkit data validate` stays clean on an adopter's tree."""
    from jsonschema import Draft202012Validator
    from ruamel.yaml import YAML

    cap = _capability_tree(_repo(tmp_path / "repo", origin="git@github.com:acme/x.git"))
    path = gate.write_stamp(cap, by=gate.BY_BOOTSTRAP)
    schema = json.loads(
        (CAPABILITY / "schemas" / "bootstrap-stamp.schema.json").read_text(
            encoding="utf-8"
        )
    )
    document = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    assert [e.message for e in Draft202012Validator(schema).iter_errors(document)] == []


def test_stamp_records_the_bootstrapping_capability_version(gate, tmp_path):
    cap = _capability_tree(_repo(tmp_path / "repo"))
    _stamp(gate, cap)
    assert gate.evaluate(cap).stamp.capability_version == "0.54.0"


# --- a stamp that attests nothing ----------------------------------------


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("schema_version: 1\n", "no `bootstrap:` block"),
        ("schema_version: 1\nbootstrap: {}\n", "no `bootstrap.completed_at`"),
        (
            "schema_version: 1\nbootstrap:\n  completed_at: '2026-01-01T00:00:00+00:00'\n",
            "no `bootstrap.capability_version`",
        ),
        ("- not\n- a\n- mapping\n", "not a YAML mapping"),
        ("bootstrap: [\n", "unreadable"),
    ],
    ids=["no-block", "empty-block", "no-version", "not-a-mapping", "unparseable"],
)
def test_a_stamp_that_attests_nothing_is_refused(gate, tmp_path, content, expected):
    """Every deviation from the expected stamp shape reads as NOT bootstrapped.
    An unreadable prerequisite must never read as a satisfied one."""
    cap = _capability_tree(_repo(tmp_path / "repo"))
    gate.stamp_path(cap).write_text(content, encoding="utf-8")
    outcome = gate.evaluate(cap)
    assert not outcome.ok
    assert expected in outcome.reason


# --- config shape (a config can break after a successful bootstrap) ------


def test_stamped_but_missing_config_is_refused(gate, tmp_path):
    cap = _capability_tree(_repo(tmp_path / "repo"), config=None)
    _stamp(gate, cap)
    outcome = gate.evaluate(cap)
    assert not outcome.ok
    assert "adopter config is missing" in outcome.reason


def test_stamped_but_config_missing_a_required_key_is_refused(gate, tmp_path):
    cap = _capability_tree(_repo(tmp_path / "repo"), config="schema_version: 1\n")
    _stamp(gate, cap)
    outcome = gate.evaluate(cap)
    assert not outcome.ok
    assert "missing required key(s)" in outcome.reason
    assert "default_branch" in outcome.reason


def test_stamped_but_config_with_a_misspelled_key_is_refused(gate, tmp_path):
    """The #689 failure the config schema was built for: a trailing `s` on
    `has_projects_v2_board` is silently ignored by every reader and leaves the
    adopter in label-fallback mode. The gate refuses and names the key."""
    cap = _capability_tree(
        _repo(tmp_path / "repo"),
        config=(
            "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"
            "has_projects_v2_boards: true\n"
        ),
    )
    _stamp(gate, cap)
    outcome = gate.evaluate(cap)
    assert not outcome.ok
    assert "has_projects_v2_boards" in outcome.reason


def test_stamped_but_unparseable_config_is_refused(gate, tmp_path):
    cap = _capability_tree(_repo(tmp_path / "repo"), config="default_branch: [\n")
    _stamp(gate, cap)
    outcome = gate.evaluate(cap)
    assert not outcome.ok
    assert "unreadable" in outcome.reason


def test_config_shape_is_skipped_when_the_companion_schema_is_absent(gate, tmp_path):
    """Honesty: with no companion schema to derive the rules from, the gate does
    not invent a verdict — the stamp still gates, the shape check stands down
    (a corrupt install is pre-check's diagnosis, not a fabricated refusal)."""
    cap = _capability_tree(_repo(tmp_path / "repo"), config="anything: goes\n")
    (cap / "schemas" / "config.schema.json").unlink()
    _stamp(gate, cap)
    assert gate.evaluate(cap).ok


# --- the repo binding ----------------------------------------------------


def test_a_stamp_from_another_repo_is_refused(gate, tmp_path):
    """A stamp is adopter state under the seed-once `project/` subtree, so it
    travels — by a fresh capability install seeding `project/` from source, or
    by someone copying another project's `.pkit/` tree. A stamp naming a
    different repo attests nothing about this one."""
    cap = _capability_tree(_repo(tmp_path / "repo", origin="git@github.com:acme/x.git"))
    _stamp(gate, cap, repo="github.com/someone-else/other")
    outcome = gate.evaluate(cap)
    assert not outcome.ok
    assert "written for a different repository" in outcome.reason


def test_the_same_repo_over_a_different_transport_still_passes(gate, tmp_path):
    """ssh and https spellings of one remote are the same repo — the binding
    must not false-refuse on a re-clone over the other transport."""
    cap = _capability_tree(
        _repo(tmp_path / "repo", origin="https://github.com/acme/x.git")
    )
    _stamp(gate, cap, repo=gate.normalize_repo_identity("git@github.com:acme/x.git"))
    assert gate.evaluate(cap).ok


def test_an_unbound_stamp_passes(gate, tmp_path):
    """A stamp with no `repo:` (what the grandfathering migration writes, and
    what a repo with no origin produces) is honoured: the binding is a defence
    against a travelling stamp, not an extra requirement."""
    cap = _capability_tree(_repo(tmp_path / "repo", origin="git@github.com:acme/x.git"))
    _stamp(gate, cap, repo=None)
    assert gate.evaluate(cap).ok


def test_an_unresolvable_local_identity_does_not_fabricate_a_refusal(
    gate, tmp_path, monkeypatch
):
    """When this side's identity cannot be resolved (no git, no origin), the
    binding stands down rather than blocking — the gate never claims a verdict
    it cannot back."""
    cap = _capability_tree(_repo(tmp_path / "repo"))  # no origin remote
    _stamp(gate, cap, repo="github.com/acme/x")
    monkeypatch.setattr(gate, "current_repo_identity", lambda *_a, **_k: None)
    assert gate.evaluate(cap).ok


# --- staleness is a signal, not a refusal --------------------------------


def test_a_stale_stamp_still_passes_but_is_flagged(gate, tmp_path):
    """The stamp records which capability version bootstrapped so an upgrade
    whose bootstrap obligations changed is DETECTABLE. It is reported, not
    refused: most upgrades change nothing about bootstrap, and refusing on
    drift would break every command after every upgrade."""
    cap = _capability_tree(_repo(tmp_path / "repo"))
    _stamp(gate, cap, capability_version="0.17.0")
    outcome = gate.evaluate(cap)
    assert outcome.ok
    assert outcome.stale
    note = gate.staleness_note(outcome)
    assert "0.17.0" in note and "0.54.0" in note


def test_a_current_stamp_is_not_stale(gate, tmp_path):
    cap = _capability_tree(_repo(tmp_path / "repo"))
    _stamp(gate, cap)
    outcome = gate.evaluate(cap)
    assert outcome.ok
    assert not outcome.stale
    assert gate.staleness_note(outcome) is None


# --- the exemption list, and failing closed ------------------------------


def test_the_exemption_list_is_the_five_decided_verbs(gate):
    """The decided set, with a reason recorded per verb: each is either how you
    BECOME bootstrapped or how you DIAGNOSE why you are not."""
    assert set(gate.EXEMPT_VERBS) == {
        "bootstrap",
        "pre-check",
        "migrate",
        "adopt-existing",
        "self-test",
    }
    assert all(reason.strip() for reason in gate.EXEMPT_VERBS.values())


def test_a_gate_that_cannot_evaluate_fails_closed(gate, tmp_path, monkeypatch, capsys):
    """An unexpected failure inside the gate must refuse, not wave the command
    through — waving it through is the fail-open behaviour #747 removes."""

    def _boom(_root=None):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(gate, "evaluate", _boom)
    assert gate.enforce("close-issue", capability_root=tmp_path) is False
    assert "could not be evaluated" in capsys.readouterr().err


def test_help_requests_pass_only_when_explicitly_allowed(gate, tmp_path, monkeypatch):
    """`allow_help` exists for the entry points whose argparse lives in a shared
    runner, where the gate necessarily runs before `--help` would be answered.
    It is opt-in: without it, a help flag is not special."""
    cap = _capability_tree(_repo(tmp_path / "repo"))  # un-bootstrapped
    monkeypatch.setattr(sys, "argv", ["check-criterion", "--help"])
    assert gate.enforce("check-criterion", capability_root=cap, allow_help=True) is True
    assert gate.enforce("check-criterion", capability_root=cap) is False
