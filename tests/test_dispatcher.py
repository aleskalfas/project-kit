"""Tests for the capability-command dispatcher (per COR-021).

Covers registration round-trip (capability install -> commands surface;
uninstall -> commands disappear), the verb-subject + noun-only command
shapes, error UX for unknown subcommands, and the proxy contract
(args + exit code passthrough).
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import install as install_mod
from project_kit.cli import main
from project_kit.manifest import ComponentRegistryEntry, read_backbone_manifest, write_backbone_manifest


# --- fixtures ---------------------------------------------------------


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal adopter project with `.pkit/` initialised."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")

    def _noop(_script: Path, _ctx: install_mod.InstallContext) -> None:
        return None

    monkeypatch.setattr(install_mod, "_run_adapter_primitive", _noop)
    install_mod.install_kit(tmp_path)
    return tmp_path


def _install_synthetic_capability(
    target: Path,
    name: str,
    *,
    commands_yaml: str = "",
    description: str = "Synthetic capability for dispatcher tests.",
) -> Path:
    """Place a synthetic capability directly under `.pkit/capabilities/<name>/`.

    Skips the regular install flow (which copies from a kit source) so
    tests can build capabilities with arbitrary `commands:` shapes
    without staging in a separate kit source.

    Returns the capability directory.
    """
    cap_dir = target / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"""schema_version: 2
component:
  kind: capability
  name: {name}
  version: 0.1.0
description: {description}
requires_backbone: ">=0.1.0,<99.0.0"
{commands_yaml}
""",
        encoding="utf-8",
    )

    # Register in the backbone manifest.
    backbone = read_backbone_manifest(target)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=name,
            manifest=f".pkit/capabilities/{name}/manifest.yaml",
        )
    )
    write_backbone_manifest(target, backbone)
    return cap_dir


def _stage_proxy_script(
    cap_dir: Path,
    relative_path: str,
    *,
    exit_code: int = 0,
    body: str = "",
) -> Path:
    """Write an executable Python script under the capability that prints its args.

    The script writes its argv + cwd + an optional `body` marker to
    stdout, then exits with `exit_code`. Used by proxy-contract tests.
    """
    script_path = cap_dir / relative_path
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        f"""#!/usr/bin/env python3
import sys
print("argv:", sys.argv[1:])
{body}
sys.exit({exit_code})
""",
        encoding="utf-8",
    )
    script_path.chmod(
        script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )
    return script_path


# --- registration round-trip -----------------------------------------


def test_no_capabilities_installed_means_no_extra_commands(kit_target: Path) -> None:
    """The dispatcher is a no-op when no capabilities are installed."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    # version is a kit-internal command and must still surface.
    assert "version" in result.output


def test_installed_capability_with_commands_surfaces_in_main_help(
    kit_target: Path,
) -> None:
    """An installed capability's namespace appears in `pkit --help`."""
    _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping marker.\n"
        ),
    )
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "demo" in result.output


def test_installed_capability_without_commands_does_not_surface(
    kit_target: Path,
) -> None:
    """A capability without a `commands:` block contributes no namespace."""
    _install_synthetic_capability(kit_target, "silent")
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "silent" not in result.output


def test_capability_subcommand_lists_via_capability_help(kit_target: Path) -> None:
    """`pkit <capability> --help` lists the capability's commands."""
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping marker.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/ping.py")
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "--help"])
    assert result.exit_code == 0
    assert "ping" in result.output


# --- verb-subject + noun-only shapes ---------------------------------


def test_verb_subject_subcommand_proxies_to_script(
    kit_target: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """`pkit <cap> <verb> <subject>` resolves through a nested sub-group."""
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  create:\n"
            "    issue:\n"
            "      script: scripts/create-issue.py\n"
            "      help: File an issue.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/create-issue.py")
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "create", "issue", "--type=task"])
    assert result.exit_code == 0
    captured = capfd.readouterr()
    assert "argv: ['--type=task']" in captured.out


def test_noun_only_subcommand_proxies_to_script(
    kit_target: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """`pkit <cap> <command>` resolves to a flat top-level leaf."""
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  pre-check:\n"
            "    script: scripts/pre-check.py\n"
            "    help: Verify prerequisites.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/pre-check.py")
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "pre-check"])
    assert result.exit_code == 0
    captured = capfd.readouterr()
    assert "argv: []" in captured.out


def test_noun_only_and_verb_subject_coexist_in_one_capability(
    kit_target: Path,
) -> None:
    """A capability can ship both flat top-level commands and nested verb-subject."""
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  pre-check:\n"
            "    script: scripts/pre-check.py\n"
            "    help: Verify prerequisites.\n"
            "  create:\n"
            "    issue:\n"
            "      script: scripts/create-issue.py\n"
            "      help: File an issue.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/pre-check.py")
    _stage_proxy_script(cap_dir, "scripts/create-issue.py")
    runner = CliRunner()

    flat = runner.invoke(main, ["demo", "pre-check"])
    nested = runner.invoke(main, ["demo", "create", "issue"])
    assert flat.exit_code == 0
    assert nested.exit_code == 0


# --- proxy contract --------------------------------------------------


def test_proxy_passes_arguments_verbatim_to_script(
    kit_target: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """All args after the resolved subcommand pass through to the script."""
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  echo:\n"
            "    script: scripts/echo.py\n"
            "    help: Echo argv.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/echo.py")
    runner = CliRunner()
    result = runner.invoke(
        main, ["demo", "echo", "--flag", "value", "--", "positional"]
    )
    assert result.exit_code == 0
    captured = capfd.readouterr()
    assert "--flag" in captured.out
    assert "value" in captured.out
    assert "positional" in captured.out


def test_proxy_returns_script_exit_code(kit_target: Path) -> None:
    """The script's exit code becomes the CLI's exit code."""
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  fail:\n"
            "    script: scripts/fail.py\n"
            "    help: Exit non-zero.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/fail.py", exit_code=42)
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "fail"])
    assert result.exit_code == 42


def test_proxy_passes_help_flag_through_to_script(
    kit_target: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """`--help` on a leaf command goes to the script, not Click's built-in.

    Capability scripts opt into their own `--help` convention; Click's
    framework `--help` is suppressed on leaves per COR-021's discover-
    ability contract.
    """
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  echo:\n"
            "    script: scripts/echo.py\n"
            "    help: Echo argv.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/echo.py")
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "echo", "--help"])
    assert result.exit_code == 0
    captured = capfd.readouterr()
    assert "--help" in captured.out


def test_proxy_reports_missing_script_clearly(kit_target: Path) -> None:
    """When a declared script doesn't exist on disk, the dispatcher fails clearly."""
    _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  missing:\n"
            "    script: scripts/never-staged.py\n"
            "    help: Points at a non-existent file.\n"
        ),
    )
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "missing"])
    assert result.exit_code != 0
    assert "script not found" in result.output


# --- unknown namespace / subcommand ----------------------------------


def test_unknown_capability_namespace_errors_with_nonzero_exit(
    kit_target: Path,
) -> None:
    """An unknown top-level token produces a Click error."""
    runner = CliRunner()
    result = runner.invoke(main, ["nonexistent-capability"])
    assert result.exit_code != 0


def test_unknown_subcommand_under_known_capability_errors(kit_target: Path) -> None:
    """An unknown subcommand within a known capability produces a Click error."""
    _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping marker.\n"
        ),
    )
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "bogus-subcommand"])
    assert result.exit_code != 0


# --- conflict resolution ---------------------------------------------


def test_kit_internal_command_wins_when_capability_name_matches(
    kit_target: Path,
) -> None:
    """A capability whose name collides with a kit-internal command is unreachable.

    Per COR-021's name-resolution-on-conflict rule, kit-internal
    commands win on resolution. The capability still installs, but its
    namespace is shadowed by the kit-internal command.
    """
    _install_synthetic_capability(
        kit_target,
        "version",  # collides with `pkit version`
        commands_yaml=(
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Should be unreachable.\n"
        ),
    )
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    # The kit-internal `version` command resolves and prints its output.
    assert result.exit_code == 0
    assert "pkit " in result.output  # the kit-internal version output


# --- aliases (#192) ---------------------------------------------------


def test_capability_alias_surfaces_in_main_help(kit_target: Path) -> None:
    """A capability that declares `aliases:` in package.yaml registers each alias."""
    _install_synthetic_capability(
        kit_target,
        "demo-capability",
        commands_yaml=(
            "aliases:\n"
            "  - dc\n"
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping.\n"
        ),
    )
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "demo-capability" in result.output
    assert "dc" in result.output


def test_alias_resolves_to_same_subcommands_as_canonical(
    kit_target: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """`pkit <alias> <sub>` proxies to the same script as `pkit <canonical> <sub>`."""
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo-capability",
        commands_yaml=(
            "aliases:\n"
            "  - dc\n"
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/ping.py", body='print("pong")')
    runner = CliRunner()
    canonical = runner.invoke(main, ["demo-capability", "ping"])
    assert canonical.exit_code == 0
    canonical_output = capfd.readouterr().out
    via_alias = runner.invoke(main, ["dc", "ping"])
    assert via_alias.exit_code == 0
    via_alias_output = capfd.readouterr().out
    assert "pong" in canonical_output
    assert via_alias_output == canonical_output


def test_canonical_capability_name_wins_over_alias_collision(
    kit_target: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """If a capability's canonical name collides with another's alias, canonical wins.

    Per the dispatcher's resolution rule: canonical names register
    first; aliases only fill slots not already claimed. The second
    capability's alias `cap-a` is shadowed by the first capability's
    actual name `cap-a`.
    """
    cap_a = _install_synthetic_capability(
        kit_target,
        "cap-a",
        commands_yaml=(
            "commands:\n"
            "  ping:\n"
            "    script: scripts/a-ping.py\n"
            "    help: A's ping.\n"
        ),
    )
    cap_b = _install_synthetic_capability(
        kit_target,
        "cap-b",
        commands_yaml=(
            "aliases:\n"
            "  - cap-a\n"  # collides with cap-a's canonical name
            "commands:\n"
            "  ping:\n"
            "    script: scripts/b-ping.py\n"
            "    help: B's ping.\n"
        ),
    )
    _stage_proxy_script(cap_a, "scripts/a-ping.py", body='print("from A")')
    _stage_proxy_script(cap_b, "scripts/b-ping.py", body='print("from B")')

    runner = CliRunner()
    result = runner.invoke(main, ["cap-a", "ping"])
    assert result.exit_code == 0
    captured = capfd.readouterr().out
    assert "from A" in captured
    assert "from B" not in captured


def test_capability_without_aliases_field_works_unchanged(
    kit_target: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """Capabilities that don't declare `aliases:` behave exactly as before.

    Backwards-compat guard: the field is optional; absence must not
    affect existing dispatch.
    """
    cap_dir = _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping.\n"
        ),
    )
    _stage_proxy_script(cap_dir, "scripts/ping.py", body='print("pong")')
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "ping"])
    assert result.exit_code == 0
    assert "pong" in capfd.readouterr().out


def test_alias_malformed_field_is_ignored(kit_target: Path) -> None:
    """An `aliases:` field that's not a list of strings is silently ignored.

    Defensive guard: malformed manifests should not break the
    dispatcher; the capability still registers under its canonical
    name. (A pre-check schema validator could surface the error
    separately — out of scope here.)
    """
    _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "aliases: 'not-a-list'\n"  # malformed (string, not list)
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping.\n"
        ),
    )
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "demo" in result.output


# --- uninstall round-trip --------------------------------------------


def test_uninstalled_capability_does_not_surface(kit_target: Path) -> None:
    """After uninstall, the capability's namespace disappears from `--help`."""
    _install_synthetic_capability(
        kit_target,
        "demo",
        commands_yaml=(
            "commands:\n"
            "  ping:\n"
            "    script: scripts/ping.py\n"
            "    help: Print a ping marker.\n"
        ),
    )
    runner = CliRunner()
    before = runner.invoke(main, ["--help"])
    assert "demo" in before.output

    # Simulate uninstall by removing from manifest + filesystem.
    backbone = read_backbone_manifest(kit_target)
    assert backbone is not None
    backbone.components = [
        c for c in backbone.components if not (c.kind == "capability" and c.name == "demo")
    ]
    write_backbone_manifest(kit_target, backbone)
    cap_dir = kit_target / ".pkit" / "capabilities" / "demo"
    import shutil
    shutil.rmtree(cap_dir)

    after = runner.invoke(main, ["--help"])
    assert "demo" not in after.output
