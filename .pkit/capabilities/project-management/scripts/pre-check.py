#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — pre-check.

Read-only diagnostic that verifies every prerequisite the methodology
depends on is in place before any pm operation runs. Compares the
adopter's GitHub state and project-side configuration against the
capability's schemas; reports every gap with a remediation hint.

Contract per the capability's DEC-017-prerequisites-bootstrap-migrate-
discipline. Programmatic, not AI-mediated; exit code is the contract.

Self-contained via PEP 723 inline metadata: run via
  uv run --script .pkit/capabilities/project-management/scripts/pre-check.py

Exit codes:
  0  every check passed or was legitimately skipped
  1  one or more checks failed
  2  usage error (script invoked outside an adopter; capability not
     installed at the expected path; config file unparseable in a way
     that blocks the script from running at all)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

# Shared deployed-agent resolution (one deploy-path definition across
# pre-check and the DEC-032 contribution collector, per COR-007) and the
# DEC-032 contribution collector itself (reused, not re-implemented).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import axis_labels  # noqa: E402
from _lib.agents import agent_deploy_path, agent_is_deployed  # noqa: E402
from _lib.gh import gh_project_run  # noqa: E402
from _lib.review_contributions import collect_contributions  # noqa: E402


CAPABILITY_NAME = "project-management"
ADOPTER_CONFIG_PATH = "project/config.yaml"
REQUIRED_ADOPTER_CONFIG_FIELDS = ("schema_version", "default_branch", "workstreams")


@dataclass(frozen=True)
class CheckResult:
    """One check's outcome."""

    label: str
    status: str  # "ok" | "fail" | "skip"
    detail: str
    remediation: str | None = None


# ----- script entry --------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify project-management capability prerequisites are in place. "
            "Exit 0 if every check passes or is legitimately skipped; "
            "non-zero on any failure."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            "(default: <repo-root>/.pkit/capabilities/project-management/)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text.",
    )
    args = parser.parse_args()

    capability_root = _resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            "error: project-management capability not found. "
            "Run this script from within an adopter project that has the "
            "capability installed at .pkit/capabilities/project-management/.",
            file=sys.stderr,
        )
        return 2

    if not args.json:
        _print_context_header(capability_root)

    results = _run_all_checks(capability_root)

    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
    else:
        _print_human(results)

    return 0 if all(r.status != "fail" for r in results) else 1


def _print_context_header(capability_root: Path) -> None:
    """Print the target repo + capability + config paths before any checks.

    Surfaces *which* repo and *which* capability install the script is
    operating on. Defensive against running the script in the wrong
    project tree (multiple checkouts open, wrong cwd, etc.).
    """
    repo = _resolve_repo_name_with_owner()
    version = _read_capability_version(capability_root)
    config_path = capability_root / ADOPTER_CONFIG_PATH

    print("pre-check: project-management capability")
    print(f"  target repo: {repo}")
    print(f"  capability:  {capability_root} (v{version})")
    print(f"  config:      {config_path}")
    print()


def _resolve_repo_name_with_owner() -> str:
    """Best-effort `<owner>/<repo>` for the current working tree.

    Returns `<unresolved>` when `gh repo view` fails — the relevant
    check downstream will surface the same failure with proper detail.
    """
    proc = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "<unresolved>"
    try:
        return json.loads(proc.stdout).get("nameWithOwner", "<unresolved>")
    except json.JSONDecodeError:
        return "<unresolved>"


def _read_capability_version(capability_root: Path) -> str:
    """Read the capability's installed version from its package.yaml."""
    pkg = capability_root / "package.yaml"
    if not pkg.is_file():
        return "<unknown>"
    try:
        data = YAML(typ="safe").load(pkg.read_text(encoding="utf-8")) or {}
        return str(data.get("component", {}).get("version", "<unknown>"))
    except (OSError, YAMLError):
        return "<unknown>"


# ----- check orchestration -------------------------------------------


def _run_all_checks(capability_root: Path) -> list[CheckResult]:
    """Run every check in fixed order. Each check is independent."""
    results: list[CheckResult] = []

    # 1+2. Tooling on PATH (git, gh) — every other check depends on these.
    results.append(_check_command_on_path("git"))
    gh_result = _check_command_on_path("gh")
    results.append(gh_result)

    if gh_result.status == "fail":
        # Without gh, the remaining checks can't run — short-circuit.
        results.append(
            CheckResult(
                "remaining checks",
                "skip",
                "skipped — `gh` not on PATH",
            )
        )
        return results

    # 3. gh authentication.
    results.append(_check_gh_auth())

    # Adopter config — read once; needed by checks 4, 6, 7.
    config_path = capability_root / ADOPTER_CONFIG_PATH
    config, config_result = _check_adopter_config(config_path)
    results.append(config_result)

    # Substrate map — read once (per DEC-036 / ADR-026). `None` ⇒ greenfield
    # (no map): every axis is served via the kit's own labels, so the label
    # checks below run exactly as before. A map present flips the axis checks
    # from hard-refuse-on-missing-label to a capability matrix (served via
    # binding / advisory / disabled) — pre-check degrades, never refuses.
    substrate_map = axis_labels.load_substrate_map(capability_root)
    if substrate_map is not None:
        # A present map that the loader fail-closed to degrade-all (no axes)
        # is ambiguous between a typo'd file and a deliberate all-`unsupported`
        # config — the loader cannot tell them apart and reports neither. Probe
        # the file distinctly so a malformed map is diagnosable, not silent
        # (G-3 / the loader docstring's promise).
        results.append(_check_substrate_map_parse(capability_root))
        results.extend(_check_substrate_capability_matrix(substrate_map))

    # 3b. gh: block validation + host-pinned auth (per DEC-023).
    if config is not None:
        results.append(_check_gh_block(config))
        results.append(_check_gh_host_auth(config))

    # 4. Repo accessibility.
    results.append(_check_repo_accessible())

    # 5. Board id resolves (conditional).
    has_board = bool(config and config.get("has_projects_v2_board"))
    if has_board:
        board_id = config.get("projects_v2_board_id") if config else None
        # Thread the repo's OWNER so `_check_board` can resolve an org-owned
        # board (#444). `_resolve_repo_name_with_owner` returns `owner/name`; the
        # owner segment is what `gh project view --owner` needs. A `<unresolved>`
        # result has no `/`, so `owner` stays None and the check falls back to the
        # cache (if present) or an ownerless view.
        name_with_owner = _resolve_repo_name_with_owner()
        board_owner = name_with_owner.split("/", 1)[0] if "/" in name_with_owner else None
        results.append(_check_board(board_id, config=config, owner=board_owner))
    else:
        results.append(
            CheckResult(
                "Projects v2 board",
                "skip",
                "no board configured (label-fallback mode)",
            )
        )

    # 6. Required labels (classification axes + state labels in label-fallback).
    #    A bound/unsupported axis (substrate_map present) degrades rather than
    #    demanding the kit's own labels exist; greenfield is unchanged.
    results.extend(_check_labels(capability_root, config, has_board, substrate_map))

    # 6b. State labels presence (label-fallback mode only). A `state` axis bound
    #     to a `derive` predicate (or unsupported) has no `state:*` labels to
    #     check — degrade, don't refuse.
    if not has_board:
        results.append(_check_state_labels(capability_root, substrate_map))

    # 7. Default branch matches config.
    results.append(_check_default_branch(config))

    # 8. workstreams.yaml parses cleanly (DEC-018; check applies even when
    #    the file is absent — that's the legitimate pre-migration state).
    results.append(_check_workstreams_file(capability_root))

    # 9. mandatory-issue-state.yaml parses cleanly (DEC-019).
    results.append(_check_mandatory_state_schema(capability_root))

    # 10. mesh_peers / mesh_source URI validation (DEC-022).
    results.append(_check_mesh_config(config))

    # 11. hooks.yaml shape + per-kind validation (DEC-024).
    results.extend(_check_hooks_file(capability_root))

    # 12. review: block validation (DEC-027 + DEC-028).
    if config is not None:
        results.extend(_check_review_block(config, capability_root))

    # 13. Title-prefix alignment (sample of open issues cross-validated
    #     against issue-types.yaml + classification.yaml prefixes). Under a
    #     present map the `type` axis may be bound to the adopter's own title
    #     prefixes (or unsupported/derived) — so the kit's prefix vocabulary is
    #     not the right yardstick and a mismatch must degrade, never refuse.
    results.extend(_check_title_prefix_alignment(capability_root, substrate_map))

    return results


# ----- individual checks ---------------------------------------------


def _check_command_on_path(cmd: str) -> CheckResult:
    if shutil.which(cmd) is None:
        return CheckResult(
            f"`{cmd}` on PATH",
            "fail",
            f"`{cmd}` not found on PATH",
            remediation=(
                f"Install `{cmd}` and ensure it is invocable from the shell. "
                f"This script (and the project-manager) require it for all operations."
            ),
        )
    # Capture version for diagnostics; not part of the gate.
    try:
        proc = subprocess.run(
            [cmd, "--version"], capture_output=True, text=True, check=False
        )
        version_line = proc.stdout.strip().split("\n", maxsplit=1)[0] if proc.stdout else ""
    except OSError:
        version_line = ""
    detail = f"present" + (f" ({version_line})" if version_line else "")
    return CheckResult(f"`{cmd}` on PATH", "ok", detail)


def _check_gh_auth() -> CheckResult:
    """Verify `gh auth status` reports an authenticated host (ambient)."""
    proc = subprocess.run(
        ["gh", "auth", "status"], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        return CheckResult(
            "`gh` authenticated",
            "fail",
            "`gh auth status` reports no active authentication",
            remediation="Run `gh auth login` and follow the prompts.",
        )
    # First line of `gh auth status` typically names the host.
    first_line = (proc.stderr or proc.stdout).strip().split("\n", maxsplit=1)[0]
    return CheckResult("`gh` authenticated", "ok", first_line)


def _check_gh_block(config: dict[str, Any]) -> CheckResult:
    """Validate the optional `gh:` block per DEC-023.

    Shape rules:
    - The block is optional; if absent or `null`, the check passes (skipped).
    - When present, it must be a YAML mapping.
    - Allowed keys: `host`, `default_owner`. Both optional.
    - Each declared value must be a non-empty string.
    - Extra keys are flagged (`additionalProperties: false` per DEC-023).
    """
    raw = config.get("gh")
    if raw is None:
        return CheckResult(
            "`gh:` config block",
            "skip",
            "no `gh:` block configured (using ambient `gh` state)",
        )
    if not isinstance(raw, dict):
        return CheckResult(
            "`gh:` config block valid",
            "fail",
            "`gh:` is present but not a mapping",
            remediation=(
                "Make `gh:` a YAML mapping with optional `host:` and "
                "`default_owner:` string fields, or remove it entirely "
                "to delegate to ambient state. See DEC-023."
            ),
        )

    allowed = {"host", "default_owner"}
    extras = sorted(set(raw.keys()) - allowed)
    if extras:
        return CheckResult(
            "`gh:` config block valid",
            "fail",
            f"unknown key(s) under `gh:`: {', '.join(extras)}",
            remediation=(
                "Remove the unknown keys. DEC-023 allows only `host:` and "
                "`default_owner:` under `gh:` at v1; per-resource granularity "
                "is deferred to a future record."
            ),
        )

    for field in ("host", "default_owner"):
        value = raw.get(field)
        if value is None:
            continue  # absent is fine
        if not isinstance(value, str) or not value:
            return CheckResult(
                "`gh:` config block valid",
                "fail",
                f"`gh.{field}` must be a non-empty string when set; got {value!r}",
                remediation=(
                    f"Either remove `{field}:` from `gh:` or set it to a "
                    "non-empty string."
                ),
            )

    summary_parts: list[str] = []
    if raw.get("host"):
        summary_parts.append(f"host={raw['host']}")
    if raw.get("default_owner"):
        summary_parts.append(f"default_owner={raw['default_owner']}")
    summary = ", ".join(summary_parts) if summary_parts else "empty block (no overrides)"
    return CheckResult("`gh:` config block valid", "ok", summary)


def _check_gh_host_auth(config: dict[str, Any]) -> CheckResult:
    """When `gh.host` is set, verify `gh auth status -h <host>` succeeds.

    Per DEC-023's adopter-portability discipline: a correct `config.yaml`
    should be enough for any team member or agent to reach the configured
    host. If `gh` isn't authenticated against the configured host, the
    pre-check fails early with a remediation pointing at `gh auth login`.
    """
    host = (config.get("gh") or {}).get("host") if isinstance(config.get("gh"), dict) else None
    if not isinstance(host, str) or not host:
        return CheckResult(
            "`gh` authenticated against configured host",
            "skip",
            "no `gh.host` configured",
        )
    proc = subprocess.run(
        ["gh", "auth", "status", "-h", host],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult(
            "`gh` authenticated against configured host",
            "fail",
            f"`gh auth status -h {host}` reports no active authentication",
            remediation=(
                f"Run `gh auth login -h {host}` and follow the prompts. "
                "DEC-023 requires the adopter's configured host to be "
                "authenticated locally."
            ),
        )
    return CheckResult(
        "`gh` authenticated against configured host", "ok", f"host={host}"
    )


def _check_adopter_config(
    path: Path,
) -> tuple[dict[str, Any] | None, CheckResult]:
    if not path.is_file():
        return None, CheckResult(
            "adopter config present",
            "fail",
            f"missing at {path}",
            remediation=(
                "Author a project-side config at "
                "`.pkit/capabilities/project-management/project/config.yaml` "
                "declaring at minimum: schema_version, default_branch, "
                "workstreams, has_projects_v2_board. See the capability "
                "README's 'Adopter setup' section."
            ),
        )
    try:
        text = path.read_text(encoding="utf-8")
        data = YAML(typ="safe").load(text) or {}
    except (OSError, YAMLError) as exc:
        return None, CheckResult(
            "adopter config parses",
            "fail",
            f"failed to read/parse {path}: {exc}",
            remediation="Fix YAML syntax; re-run.",
        )
    if not isinstance(data, dict):
        return None, CheckResult(
            "adopter config parses",
            "fail",
            f"{path} top-level is not a mapping",
            remediation="The config must be a YAML mapping at the top level.",
        )
    missing = [f for f in REQUIRED_ADOPTER_CONFIG_FIELDS if f not in data]
    if missing:
        return data, CheckResult(
            "adopter config has required fields",
            "fail",
            f"missing fields in {path}: {', '.join(missing)}",
            remediation=(
                "Add the missing fields. See DEC-017 for the expected shape; "
                "the capability README documents each field."
            ),
        )
    return data, CheckResult(
        "adopter config present + valid",
        "ok",
        f"{path} parses; required fields present",
    )


def _check_repo_accessible() -> CheckResult:
    proc = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult(
            "repo accessible",
            "fail",
            "`gh repo view` failed",
            remediation=(
                "Run the script from within a GitHub repo checkout, and "
                "ensure `gh` is authenticated against the host that owns it."
            ),
        )
    try:
        data = json.loads(proc.stdout)
        name = data.get("nameWithOwner", "<unknown>")
    except json.JSONDecodeError:
        name = "<unknown>"
    return CheckResult("repo accessible", "ok", name)


def _check_board(
    board_id: int | str | None,
    config: dict | None = None,
    owner: str | None = None,
) -> CheckResult:
    if board_id is None:
        return CheckResult(
            "Projects v2 board id",
            "fail",
            "config declares has_projects_v2_board: true but no projects_v2_board_id",
            remediation=(
                "Set `projects_v2_board_id: <N>` in the config, where <N> is "
                "the board number from `gh project list`."
            ),
        )

    # Resolving an ORG-OWNED board (#444). The prior check ran a bare
    # `gh project view <n>` with no `--owner`, which false-negatives on an
    # org-owned board: an ownerless `gh project view 2` fails, while
    # `gh project view 2 --owner <org>` (or the cached node id) resolves it.
    # The runtime create path already gets this right —
    # `create-issue._resolve_project_node_id` is cache-first on
    # `projects_v2_node_id`, and `_gh_add_to_board` threads `--owner`. This
    # health check mirrors that ordering so it accepts exactly the boards the
    # runtime accepts.
    #
    # CHOICE (cache-first, then owner-threaded fallback): trust a cached
    # `projects_v2_node_id` as sufficient evidence the board resolves before
    # making any API call. The tradeoff is CACHE STALENESS vs. an extra
    # owner-threaded round-trip — a cached id could in principle be stale (the
    # board deleted/recreated since adoption). We accept that here deliberately:
    # (a) the runtime create path trusts the SAME cache to seed board fields, so
    # a health check that distrusted it would false-alarm on a config the
    # runtime happily uses — the check must not be stricter than the thing it
    # gates; and (b) pre-check is read-only, so a stale-cache pass surfaces at
    # the first real board write (which re-resolves), not as silent corruption.
    # On a cache MISS we live-resolve with `--owner` threaded from the repo's
    # `owner/name`, which is what fixes the org-owned false-negative.
    cached_node_id = config.get("projects_v2_node_id") if isinstance(config, dict) else None
    if isinstance(cached_node_id, str) and cached_node_id:
        return CheckResult(
            "Projects v2 board",
            "ok",
            f"board #{board_id} resolves (cached node id in config)",
        )

    # Route through the `gh project` sole-constructor (#453): it threads the
    # configured `GH_HOST` (a raw `subprocess.run` would land on github.com and
    # false-negative on a GHES host) and splices `--owner` — preferring
    # `gh.default_owner`, else the repo-derived `owner` passed here.
    view_args = ["gh", "project", "view", str(board_id), "--format", "json"]
    proc = gh_project_run(view_args, config or {}, fallback_owner=owner, check=False)
    if proc.returncode != 0:
        owner_hint = f" --owner {owner}" if owner else ""
        return CheckResult(
            "Projects v2 board",
            "fail",
            f"`gh project view {board_id}{owner_hint}` failed",
            remediation=(
                "Verify the board id with `gh project list --owner <org>`. "
                "Update `projects_v2_board_id` in the config if it has moved. "
                "For an org-owned board, ensure the repo's owner owns the board "
                "(the check threads `--owner` from the repo), or cache the "
                "board's node id as `projects_v2_node_id` at adoption."
            ),
        )
    return CheckResult("Projects v2 board", "ok", f"board #{board_id} resolves")


def _axis_expects_kit_labels(
    axis: str, substrate_map: "axis_labels.SubstrateMap | None"
) -> bool:
    """Whether the kit's own `<axis>:*` labels should exist for ``axis``.

    Only in greenfield (no substrate-map). With a map present, NO axis uses the
    kit's own labels — a bound axis resolves to the adopter's substrate, an
    unsupported/absent axis degrades — so the kit-label existence check is
    skipped and replaced by the capability-matrix line. This is the read-path's
    expression of "never demand a label the adopter cannot create".
    """
    return substrate_map is None


def _axis_label_check_skipped(
    axis: str, substrate_map: "axis_labels.SubstrateMap | None"
) -> CheckResult:
    """The skip line for an axis whose kit-labels are not checked under a map."""
    disposition = axis_labels.axis_disposition(axis, substrate_map)
    if disposition == "served":
        return CheckResult(
            f"`{axis}:*` kit labels",
            "skip",
            f"axis `{axis}` bound to the adopter's substrate via "
            f"substrate-map.yaml — kit `{axis}:*` labels not required.",
        )
    return CheckResult(
        f"`{axis}:*` kit labels",
        "skip",
        f"axis `{axis}` unsupported/absent in substrate-map.yaml — degraded, "
        f"kit `{axis}:*` labels not required.",
    )


def _check_substrate_map_parse(capability_root: Path) -> CheckResult:
    """Report whether a present ``substrate-map.yaml`` actually parses + is shaped.

    The loader (:func:`axis_labels.load_substrate_map`) fail-closes a present-
    but-unparseable / mis-shaped map to *degrade-all* (a :class:`SubstrateMap`
    with no axes) — which is byte-identical to a deliberate all-``unsupported``
    config. That is the safe write-path posture, but it makes a typo'd map
    *silent*: the operator sees every axis degrade with no hint that the file is
    broken rather than intentionally empty. pre-check already re-reads the file,
    so a distinct parse/shape probe is cheap and closes that diagnosability gap
    (G-3).

    This is a lightweight shape probe, not the full JSON-Schema validation
    (`pkit schemas validate` owns that). It distinguishes three states:
      * parses to a well-formed ``axes:`` mapping ⇒ ``ok``;
      * present but YAML-unparseable, not a mapping, or no ``axes:`` mapping ⇒
        ``fail`` with a "fix the file" remediation (NOT a refusal of the run —
        the matrix still degrades every axis; this only makes the cause visible).
    """
    path = capability_root / axis_labels.SUBSTRATE_MAP_RELATIVE_PATH
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError) as exc:
        return CheckResult(
            "substrate-map.yaml parses",
            "fail",
            f"present but unparseable ({exc}) — every axis is degrading because "
            f"the file could not be read, NOT because the adopter declared it.",
            remediation=(
                "Fix the YAML syntax in project/substrate-map.yaml, then re-run. "
                "Until it parses, all axes degrade (fail-closed); this is a "
                "broken file, not a deliberate all-`unsupported` config."
            ),
        )
    if not isinstance(data, dict) or not isinstance(data.get("axes"), dict):
        return CheckResult(
            "substrate-map.yaml shape",
            "fail",
            "present but invalid — top-level must be a mapping with an `axes:` "
            "mapping. Every axis is degrading because the map is mis-shaped, NOT "
            "because the adopter declared each axis unsupported.",
            remediation=(
                "Give project/substrate-map.yaml an `axes:` mapping (per-axis "
                "binding). Run `pkit schemas validate` for the full check. Until "
                "it is well-shaped, all axes degrade (fail-closed)."
            ),
        )
    return CheckResult(
        "substrate-map.yaml parses + shaped",
        "ok",
        f"{path} parses; {len(data['axes'])} axis binding(s) declared",
    )


def _check_substrate_capability_matrix(
    substrate_map: "axis_labels.SubstrateMap",
) -> list[CheckResult]:
    """Report the per-axis capability matrix when a substrate-map is present.

    Per DEC-036 / ADR-026: with a map present, each methodology axis is either
    *served* (resolves through a declared binding) or *unsupported* (explicitly
    marked, or absent from the map — absent ≡ unsupported, the load-bearing
    rule). This surfaces the matrix as an informational block so the operator
    sees, up front, which axes the substrate can express. It never fails — a
    degraded axis is a supported brownfield state, not a misconfiguration.

    The seam's `axis_disposition` is the single source of truth for served-vs-
    degraded; pre-check renders it, it does not re-derive it.
    """
    results: list[CheckResult] = [
        CheckResult(
            "substrate-map present",
            "ok",
            "brownfield mode — axes resolve through project/substrate-map.yaml "
            "(per DEC-036). Greenfield default is no map.",
        )
    ]
    for axis in axis_labels.AXES:
        disposition = axis_labels.axis_disposition(axis, substrate_map)
        if disposition == "served":
            binding = substrate_map.axes.get(axis, {})
            kind = next(
                (k for k in ("label", "title-prefix", "derive") if k in binding),
                "?",
            )
            results.append(CheckResult(
                f"axis `{axis}` served",
                "ok",
                f"bound via `{kind}`",
            ))
        else:
            # Absent or explicitly unsupported — degrade, don't refuse.
            reason = (
                "explicitly `unsupported`"
                if axis in substrate_map.axes
                else "absent from the map (treated as unsupported, NOT greenfield)"
            )
            results.append(CheckResult(
                f"axis `{axis}` degraded",
                "skip",
                f"{reason}; rules depending on it soften to advisory where a "
                f"severity knob exists, else stay at their authored severity "
                f"(ADR-026 no-knob-stays-hard).",
            ))
    return results


def _check_labels(
    capability_root: Path,
    config: dict[str, Any] | None,
    has_board: bool,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> list[CheckResult]:
    """Verify the methodology's required labels exist on the repo.

    Greenfield (``substrate_map is None``): every axis is served via the kit's
    own labels, so each axis's labels must exist — the original hard-refuse
    behaviour, unchanged. With a map present, an axis bound to the adopter's own
    substrate (or unsupported) does NOT require the kit's `<axis>:*` labels: the
    capability matrix (`_check_substrate_capability_matrix`) already reported its
    disposition, so the per-axis kit-label check is skipped for it rather than
    failing on labels the adopter cannot create.
    """
    results: list[CheckResult] = []

    # Read classification.yaml for the type / priority axes.
    classification_path = capability_root / "schemas" / "classification.yaml"
    try:
        classification = YAML(typ="safe").load(classification_path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError) as exc:
        results.append(
            CheckResult(
                "classification.yaml readable",
                "fail",
                f"failed to read {classification_path}: {exc}",
                remediation="The capability install may be corrupt; re-install.",
            )
        )
        return results

    # Fetch existing labels once.
    proc = subprocess.run(
        ["gh", "label", "list", "--limit", "500", "--json", "name"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        results.append(
            CheckResult(
                "label list accessible",
                "fail",
                "`gh label list` failed",
                remediation="Ensure `gh` is authenticated and the repo is accessible.",
            )
        )
        return results
    try:
        existing = {label["name"] for label in json.loads(proc.stdout)}
    except (json.JSONDecodeError, KeyError, TypeError):
        existing = set()

    # Required labels: type:* always (type is always-as-label) — UNLESS a
    # substrate-map binds the axis to the adopter's own substrate, in which case
    # the kit's `type:*` labels are not expected to exist (the matrix already
    # reported the axis's disposition; fail-closed — the seam never resolves a
    # bound/unsupported axis to a kit-label write).
    if not _axis_expects_kit_labels("type", substrate_map):
        results.append(_axis_label_check_skipped("type", substrate_map))
    else:
        type_values = (
            classification.get("axes", {}).get("type", {}).get("values", [])
        )
        missing_type = [
            v for v in type_values if axis_labels.label("type", v) not in existing
        ]
        if missing_type:
            results.append(
                CheckResult(
                    "required `type:*` labels exist",
                    "fail",
                    f"missing: {', '.join(axis_labels.label('type', v) for v in missing_type)}",
                    remediation="Run `bootstrap` to create the missing labels.",
                )
            )
        else:
            results.append(
                CheckResult(
                    "required `type:*` labels exist",
                    "ok",
                    f"all {len(type_values)} labels present",
                )
            )

    # In label-fallback mode, also check priority:* and workstream:*.
    if has_board:
        results.append(
            CheckResult(
                "`priority:*` / `workstream:*` labels",
                "skip",
                "board configured — priority/workstream live as board fields",
            )
        )
    else:
        if not _axis_expects_kit_labels("priority", substrate_map):
            results.append(_axis_label_check_skipped("priority", substrate_map))
        else:
            priority_values = (
                classification.get("axes", {}).get("priority", {}).get("values", [])
            )
            missing_priority = [
                v for v in priority_values if axis_labels.label("priority", v) not in existing
            ]
            if missing_priority:
                results.append(
                    CheckResult(
                        "required `priority:*` labels exist",
                        "fail",
                        f"missing: {', '.join(axis_labels.label('priority', v) for v in missing_priority)}",
                        remediation="Run `bootstrap` to create the missing labels.",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "required `priority:*` labels exist",
                        "ok",
                        f"all {len(priority_values)} labels present",
                    )
                )

        if not _axis_expects_kit_labels("workstream", substrate_map):
            results.append(_axis_label_check_skipped("workstream", substrate_map))
            return results
        workstreams = _resolve_workstream_slugs_for_check(capability_root, config or {})
        missing_workstream = [
            w for w in workstreams if axis_labels.label("workstream", w) not in existing
        ]
        if missing_workstream:
            results.append(
                CheckResult(
                    "required `workstream:*` labels exist",
                    "fail",
                    f"missing: {', '.join(axis_labels.label('workstream', w) for w in missing_workstream)}",
                    remediation="Run `bootstrap` to create the missing labels.",
                )
            )
        elif workstreams:
            results.append(
                CheckResult(
                    "required `workstream:*` labels exist",
                    "ok",
                    f"all {len(workstreams)} labels present",
                )
            )
        else:
            results.append(
                CheckResult(
                    "`workstream:*` labels",
                    "skip",
                    "no workstreams declared in adopter config",
                )
            )

    return results


def _resolve_workstream_slugs_for_check(
    capability_root: Path, config: dict[str, Any]
) -> list[str]:
    """Read workstream slugs from workstreams.yaml or config legacy fallback."""
    ws_path = capability_root / "project" / "workstreams.yaml"
    if ws_path.is_file():
        try:
            data = YAML(typ="safe").load(ws_path.read_text(encoding="utf-8")) or {}
        except (OSError, YAMLError):
            data = {}
        ws = data.get("workstreams") if isinstance(data, dict) else None
        if isinstance(ws, list):
            return [s for s in ws if isinstance(s, str)]
        if isinstance(ws, dict):
            return [
                s
                for s, attrs in ws.items()
                if isinstance(s, str)
                and (not isinstance(attrs, dict) or attrs.get("status", "active") == "active")
            ]
        return []
    legacy = config.get("workstreams") or []
    if isinstance(legacy, list):
        return [s for s in legacy if isinstance(s, str)]
    return []


def _check_mesh_config(config: dict[str, Any] | None) -> CheckResult:
    """Validate `mesh_peers` / `mesh_source` URI shapes per DEC-022.

    Both fields are optional; absence is a clean skip. When set, each
    URI must match `github://owner/repo[/path]`.
    """
    import re as _re

    if config is None:
        return CheckResult(
            "mesh config", "skip", "adopter config not loaded"
        )
    mp = config.get("mesh_peers")
    ms = config.get("mesh_source")
    if mp is None and ms is None:
        return CheckResult(
            "mesh config",
            "skip",
            "no mesh_peers / mesh_source set (single-repo adopter)",
        )
    pattern = _re.compile(r"^github://[^/]+/[^/]+(/.*)?$")
    invalid: list[str] = []
    if mp is not None:
        if not isinstance(mp, list):
            return CheckResult(
                "mesh_peers shape",
                "fail",
                f"`mesh_peers` must be a list of github:// URIs; got {type(mp).__name__}",
                remediation="See DEC-022 for the expected shape.",
            )
        for uri in mp:
            if not isinstance(uri, str) or not pattern.match(uri):
                invalid.append(str(uri))
    if ms is not None:
        if not isinstance(ms, str) or not pattern.match(ms):
            invalid.append(str(ms))
    if invalid:
        return CheckResult(
            "mesh config URIs",
            "fail",
            f"invalid URI(s): {', '.join(invalid)}",
            remediation="URIs must match `github://<owner>/<repo>[/path]`.",
        )
    count = (len(mp) if isinstance(mp, list) else 0) + (1 if ms is not None else 0)
    return CheckResult("mesh config URIs", "ok", f"{count} URI(s) valid")


def _check_mandatory_state_schema(capability_root: Path) -> CheckResult:
    """Validate `schemas/mandatory-issue-state.yaml` parses cleanly (per DEC-019)."""
    path = capability_root / "schemas" / "mandatory-issue-state.yaml"
    if not path.is_file():
        return CheckResult(
            "mandatory-issue-state.yaml",
            "fail",
            f"missing at {path}",
            remediation="The capability install may be corrupt; re-install.",
        )
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError) as exc:
        return CheckResult(
            "mandatory-issue-state.yaml parses",
            "fail",
            f"failed to read {path}: {exc}",
            remediation="The capability install may be corrupt; re-install.",
        )
    if not isinstance(data, dict) or "required_fields" not in data:
        return CheckResult(
            "mandatory-issue-state.yaml shape",
            "fail",
            f"{path} missing `required_fields` map",
            remediation="The capability install may be corrupt; re-install.",
        )
    n = len(data.get("required_fields") or {})
    return CheckResult(
        "mandatory-issue-state.yaml present + valid",
        "ok",
        f"{path} parses; {n} required field(s) declared",
    )


def _check_workstreams_file(capability_root: Path) -> CheckResult:
    """Validate `project/workstreams.yaml` parses cleanly (per DEC-018).

    Absence is OK during the transition — the legacy `config.yaml`
    fallback covers that case. When present, the file must parse to a
    mapping with `schema_version` + `workstreams:` (list or mapping).
    """
    path = capability_root / "project" / "workstreams.yaml"
    if not path.is_file():
        return CheckResult(
            "workstreams.yaml",
            "skip",
            f"absent at {path} — legacy config.yaml fallback in effect",
        )
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError) as exc:
        return CheckResult(
            "workstreams.yaml parses",
            "fail",
            f"failed to read/parse {path}: {exc}",
            remediation="Fix YAML syntax; re-run.",
        )
    if not isinstance(data, dict):
        return CheckResult(
            "workstreams.yaml parses",
            "fail",
            f"{path} top-level is not a mapping",
            remediation="The file must be a YAML mapping at the top level.",
        )
    if "schema_version" not in data:
        return CheckResult(
            "workstreams.yaml has schema_version",
            "fail",
            f"{path} missing `schema_version` field",
            remediation="Add `schema_version: 1` at the top of the file.",
        )
    if "workstreams" not in data:
        return CheckResult(
            "workstreams.yaml has workstreams field",
            "fail",
            f"{path} missing `workstreams` field",
            remediation="Add `workstreams: ...` (list or mapping) per DEC-018.",
        )
    ws = data["workstreams"]
    if not isinstance(ws, (list, dict)):
        return CheckResult(
            "workstreams.yaml shape",
            "fail",
            f"`workstreams` must be a list or mapping; got {type(ws).__name__}",
            remediation="See DEC-018 for the two accepted forms.",
        )
    count = len(ws)
    return CheckResult(
        "workstreams.yaml present + valid",
        "ok",
        f"{path} parses; {count} entry(ies)",
    )


def _check_default_branch(config: dict[str, Any] | None) -> CheckResult:
    if config is None:
        return CheckResult(
            "default branch matches config",
            "skip",
            "adopter config not loaded",
        )
    declared = config.get("default_branch")
    if not declared:
        return CheckResult(
            "default branch matches config",
            "fail",
            "config does not declare `default_branch`",
            remediation="Add `default_branch: main` (or your project's default) to the config.",
        )
    proc = subprocess.run(
        ["gh", "repo", "view", "--json", "defaultBranchRef"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult(
            "default branch matches config",
            "fail",
            "`gh repo view` failed",
        )
    try:
        actual = json.loads(proc.stdout).get("defaultBranchRef", {}).get("name", "")
    except json.JSONDecodeError:
        actual = ""
    if actual != declared:
        return CheckResult(
            "default branch matches config",
            "fail",
            f"config declares `{declared}`; repo's default is `{actual}`",
            remediation=(
                "Update the config's `default_branch` to match the repo's "
                "default, or update the repo settings."
            ),
        )
    return CheckResult("default branch matches config", "ok", f"`{declared}`")


# ----- output --------------------------------------------------------


def _print_human(results: list[CheckResult]) -> None:
    for r in results:
        marker = {"ok": "[ok]  ", "fail": "[fail]", "skip": "[skip]"}[r.status]
        print(f"  {marker} {r.label}")
        if r.status == "fail":
            print(f"         → {r.detail}")
            if r.remediation:
                print(f"         → {r.remediation}")
        elif r.status == "skip":
            print(f"         {r.detail}")
        else:
            print(f"         {r.detail}")
    print()
    fails = sum(1 for r in results if r.status == "fail")
    oks = sum(1 for r in results if r.status == "ok")
    skips = sum(1 for r in results if r.status == "skip")
    summary = f"{fails} fail(s), {skips} skip, {oks} ok"
    if fails:
        print(f"{summary} — pre-check FAILED. Refusing to proceed.")
    else:
        print(f"{summary} — pre-check passed.")


# ----- state labels check (label-fallback mode) -----------------------


def _check_state_labels(
    capability_root: Path,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> CheckResult:
    """Verify all lifecycle state:* labels exist on the repo.

    Only relevant in label-fallback mode (has_projects_v2_board: false).
    Reads the canonical state IDs from workflow.yaml and checks each
    state:<id> label is present on the remote. Reports [fail] with a
    remediation pointer to `bootstrap` when any are missing.

    With a substrate-map present, the `state` axis no longer reads `state:*`
    labels — it is bound to a `derive` predicate (open/closed + a blocked label,
    the DEC-033 detector swap) or is unsupported. Either way the kit's `state:*`
    labels are not required; degrade to a skip rather than refuse.
    """
    if not _axis_expects_kit_labels("state", substrate_map):
        return _axis_label_check_skipped("state", substrate_map)
    workflow_path = capability_root / "schemas" / "workflow.yaml"
    try:
        wf_data = YAML(typ="safe").load(workflow_path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError) as exc:
        return CheckResult(
            "workflow.yaml readable for state-label check",
            "fail",
            f"failed to read {workflow_path}: {exc}",
            remediation="The capability install may be corrupt; re-install.",
        )

    # Since the schema_version 3 rebind (DEC-033) states live under a top-level
    # `process:` block; read there, falling back to top level for a pre-v3
    # override.
    block = wf_data.get("process") if isinstance(wf_data.get("process"), dict) else wf_data
    states = block.get("states") or []
    state_ids = [
        str(s["id"])
        for s in states
        if isinstance(s, dict) and isinstance(s.get("id"), str)
    ]
    if not state_ids:
        return CheckResult(
            "state:* labels check",
            "skip",
            "workflow.yaml declares no states (unexpected; capability may be corrupt)",
        )

    # Fetch existing labels.
    proc = subprocess.run(
        ["gh", "label", "list", "--limit", "500", "--json", "name"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult(
            "state:* labels (label-fallback)",
            "fail",
            "`gh label list` failed",
            remediation="Ensure `gh` is authenticated and the repo is accessible.",
        )
    try:
        existing = {label["name"] for label in json.loads(proc.stdout)}
    except (json.JSONDecodeError, KeyError, TypeError):
        existing = set()

    missing = [
        sid for sid in state_ids if axis_labels.label("state", sid) not in existing
    ]
    if missing:
        return CheckResult(
            "required `state:*` labels exist (label-fallback)",
            "fail",
            f"missing: {', '.join(axis_labels.label('state', s) for s in missing)}",
            remediation=(
                "Run `pkit project-management bootstrap` to create the missing "
                "state labels. These are the substrate for the move-issue state "
                "machine in label-fallback mode."
            ),
        )
    return CheckResult(
        "required `state:*` labels exist (label-fallback)",
        "ok",
        f"all {len(state_ids)} state labels present",
    )


# ----- title-prefix alignment check ----------------------------------

# Sample limit: scanning too many issues in pre-check is slow and noisy.
_TITLE_PREFIX_SAMPLE_LIMIT = 50


def _check_title_prefix_alignment(
    capability_root: Path,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> list[CheckResult]:
    """Cross-validate open issue titles against known prefix vocabularies.

    Reads issue-types.yaml and classification.yaml to build the full set
    of recognised prefixes, then samples up to _TITLE_PREFIX_SAMPLE_LIMIT
    open issues and flags any whose title prefix is unrecognised.

    Greenfield (``substrate_map is None``) — unchanged: the kit owns the title
    format, so an unrecognised or absent prefix is a hard ``fail`` (the original
    behaviour). This is the only mode in which this check returns ``fail``.

    Present map — the `type` axis may be bound to the ADOPTER's own title
    prefixes, derived, unsupported, or absent. The kit's prefix vocabulary is no
    longer the authority, so this check must DEGRADE, never refuse (per DEC-036 /
    ADR-026 "degrades, never refuses" — this was the one remaining hard-refuse
    path on the brownfield forcing case). Two sub-cases:

      * `type` bound to `title-prefix` ⇒ validate against the ADOPTER's declared
        prefixes (the binding's remap values), reported as advisory (``skip``)
        rather than ``fail`` — drift is the adopter's to fix, not a refusal.
      * `type` not served via kit-labels in any other way (bound to label/derive,
        unsupported, or absent) ⇒ the kit prefix vocabulary does not apply; skip
        the alignment entirely (the capability matrix already reported `type`'s
        disposition).

    In no present-map sub-case (native prefix, no-prefix, or unrecognised) does
    this return ``fail``.
    """
    # Build the known-prefix set.
    issue_types_path = capability_root / "schemas" / "issue-types.yaml"
    classification_path = capability_root / "schemas" / "classification.yaml"

    # Under a present map, the kit's prefix vocabulary is not the yardstick;
    # decide up front whether to validate against the adopter's prefixes or skip.
    adopter_prefixes: set[str] | None = None
    if substrate_map is not None:
        type_binding = substrate_map.axes.get("type") or {}
        prefix_binding = type_binding.get("title-prefix")
        if isinstance(prefix_binding, dict) and isinstance(
            prefix_binding.get("remap"), dict
        ):
            # `type` bound to title-prefix: validate against the adopter's own
            # declared prefixes (advisory), not the kit set.
            adopter_prefixes = {
                str(p)
                for p in prefix_binding["remap"].values()
                if isinstance(p, str) and p
            }
        else:
            # `type` bound to label/derive, unsupported, or absent — the kit
            # prefix vocabulary does not apply. Skip, do not refuse.
            return [CheckResult(
                "title-prefix alignment",
                "skip",
                "`type` axis is not served via kit title-prefixes under "
                "substrate-map.yaml — kit prefix vocabulary does not apply "
                "(see the capability matrix for `type`'s disposition).",
            )]

    known_prefixes: set[str] = set()
    try:
        it_data = YAML(typ="safe").load(issue_types_path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        it_data = {}

    types = it_data.get("types") or {}
    for entry in types.values():
        if not isinstance(entry, dict):
            continue
        prefix = entry.get("title_prefix", "")
        case = entry.get("title_case", "title")
        rendered = str(prefix).upper() if case == "upper" else str(prefix)
        if rendered:
            known_prefixes.add(rendered)

    try:
        cls_data = YAML(typ="safe").load(classification_path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        cls_data = {}

    prefix_by_value = (
        cls_data.get("axes", {}).get("type", {}).get("title_prefix_by_value", {})
    )
    for kind_prefix in prefix_by_value.values():
        if isinstance(kind_prefix, str) and kind_prefix:
            known_prefixes.add(kind_prefix)

    # Under a present map with `type` bound to title-prefix, the ADOPTER's own
    # prefixes are the yardstick — and findings are advisory, never `fail`.
    advisory = adopter_prefixes is not None
    if adopter_prefixes is not None:
        # The remap values are the full bracketed prefixes (e.g. "[Task]");
        # strip the brackets to match the `bracket_re` capture group below.
        known_prefixes = {p.strip("[]") for p in adopter_prefixes}

    if not known_prefixes:
        return [CheckResult(
            "title-prefix alignment",
            "skip",
            "could not load schemas (issue-types.yaml / classification.yaml)"
            if not advisory
            else "substrate-map.yaml binds `type` to title-prefix but declares "
            "no prefixes — nothing to validate against (degraded, not refused).",
        )]

    # Fetch a sample of open issues.
    proc = subprocess.run(
        [
            "gh", "issue", "list",
            "--state", "open",
            "--limit", str(_TITLE_PREFIX_SAMPLE_LIMIT),
            "--json", "number,title",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return [CheckResult(
            "title-prefix alignment",
            "skip",
            "`gh issue list` failed; skipping alignment check",
        )]

    try:
        issues = json.loads(proc.stdout)
    except json.JSONDecodeError:
        issues = []

    if not issues:
        return [CheckResult(
            "title-prefix alignment",
            "skip",
            "no open issues to sample",
        )]

    import re as _re
    bracket_re = _re.compile(r"^\[([^\]]+)\] ")
    mismatches: list[str] = []
    no_prefix: list[int] = []
    for issue in issues:
        title = str(issue.get("title", ""))
        number = issue.get("number", "?")
        m = bracket_re.match(title)
        if not m:
            no_prefix.append(number)
            continue
        prefix = m.group(1)
        if prefix not in known_prefixes:
            mismatches.append(f"#{number} [{prefix}]")

    results: list[CheckResult] = []
    sampled = len(issues)

    # Under a present map this whole check is advisory: a mismatch or a
    # no-prefix issue degrades to a `skip` finding, never a `fail`. Greenfield
    # keeps the original hard `fail`. `known_prefixes` here is the adopter's own
    # declared prefixes when advisory, the kit set otherwise.
    if mismatches:
        if advisory:
            results.append(CheckResult(
                "title-prefix alignment",
                "skip",
                f"{len(mismatches)} issue(s) in sample of {sampled} carry a prefix "
                f"not in the adopter's declared substrate-map prefixes "
                f"({', '.join(mismatches)}) — advisory under substrate-map.yaml, "
                f"not a refusal. Adopter prefixes: "
                + ", ".join(f"[{p}]" for p in sorted(known_prefixes)) + ".",
            ))
        else:
            results.append(CheckResult(
                "title-prefix alignment",
                "fail",
                (
                    f"{len(mismatches)} issue(s) in sample of {sampled} have unrecognised "
                    f"prefix: {', '.join(mismatches)}"
                ),
                remediation=(
                    "Update the issue titles or the prefix vocabulary in "
                    "issue-types.yaml / classification.yaml. Known prefixes: "
                    + ", ".join(f"[{p}]" for p in sorted(known_prefixes)) + "."
                ),
            ))
    else:
        results.append(CheckResult(
            "title-prefix alignment",
            "ok",
            f"all {sampled} sampled open issue(s) have recognised prefixes"
            + (" (validated against adopter substrate-map prefixes)" if advisory else ""),
        ))

    if no_prefix:
        if advisory:
            results.append(CheckResult(
                "title-prefix: issues without bracket prefix",
                "skip",
                f"{len(no_prefix)} issue(s) in sample have no `[Prefix] ` title "
                f"({', '.join(f'#{n}' for n in no_prefix[:10])}"
                + (" ..." if len(no_prefix) > 10 else "")
                + ") — advisory under substrate-map.yaml; a brownfield tracker "
                "need not bracket-prefix every issue.",
            ))
        else:
            results.append(CheckResult(
                "title-prefix: issues without bracket prefix",
                "fail",
                (
                    f"{len(no_prefix)} issue(s) in sample have no `[Prefix] ` title: "
                    f"{', '.join(f'#{n}' for n in no_prefix[:10])}"
                    + (" ..." if len(no_prefix) > 10 else "")
                ),
                remediation=(
                    "Issue titles must start with a `[Prefix] ` bracket per the "
                    "methodology's title format rules. Use edit-issue or the "
                    "project-manager to fix the titles."
                ),
            ))

    return results


# ----- hooks.yaml validation (DEC-024) --------------------------------


HOOKS_FILE_PATH = "project/hooks.yaml"
HOOK_KIT_KINDS: tuple[str, ...] = (
    "set-board-field",
    "post-comment",
    "assign-milestone",
    "custom-script",
)
HOOK_LIFECYCLE_EVENTS: tuple[str, ...] = (
    "after_create_issue",
    "after_close_issue",
    "after_open_pr",
    "after_merge_pr",
    "after_move_issue",
)


def _check_hooks_file(capability_root: Path) -> list[CheckResult]:
    """Validate `project/hooks.yaml` per DEC-024.

    Returns a list (always at least one entry) so missing / parse-only
    cases get a clear skip line, and shape errors get one finding per
    failed check.
    """
    path = capability_root / HOOKS_FILE_PATH
    if not path.is_file():
        return [CheckResult(
            "hooks.yaml present",
            "skip",
            "no hooks.yaml configured (no lifecycle hooks declared)",
        )]
    try:
        text = path.read_text(encoding="utf-8")
        data = YAML(typ="safe").load(text) or {}
    except (OSError, YAMLError) as exc:
        return [CheckResult(
            "hooks.yaml parses",
            "fail",
            f"failed to read/parse {path}: {exc}",
            remediation="Fix YAML syntax; re-run.",
        )]
    if not isinstance(data, dict):
        return [CheckResult(
            "hooks.yaml shape",
            "fail",
            f"{path} top-level is not a mapping",
            remediation="The file must be a YAML mapping at the top level.",
        )]
    if data.get("schema_version") != 1:
        return [CheckResult(
            "hooks.yaml schema_version",
            "fail",
            f"{path} missing or unexpected `schema_version` (need 1)",
            remediation="Add `schema_version: 1` at the top of the file.",
        )]
    hooks = data.get("hooks")
    if hooks is None:
        return [CheckResult(
            "hooks.yaml present + valid",
            "ok",
            f"{path} parses; no hooks declared",
        )]
    if not isinstance(hooks, dict):
        return [CheckResult(
            "hooks.yaml shape",
            "fail",
            f"`hooks:` must be a mapping; got {type(hooks).__name__}",
            remediation="Use `hooks:` as a mapping of event-name → list of hook entries.",
        )]

    results: list[CheckResult] = []
    total_entries = 0
    for event, entries in hooks.items():
        if event not in HOOK_LIFECYCLE_EVENTS:
            results.append(CheckResult(
                f"hooks.{event}",
                "fail",
                f"unknown lifecycle event {event!r}",
                remediation=f"Allowed events: {', '.join(HOOK_LIFECYCLE_EVENTS)}.",
            ))
            continue
        if not isinstance(entries, list):
            results.append(CheckResult(
                f"hooks.{event}",
                "fail",
                f"`{event}` must be a list; got {type(entries).__name__}",
                remediation="Each event maps to a YAML list of hook entries.",
            ))
            continue
        for idx, entry in enumerate(entries):
            entry_result = _validate_hook_entry(event, idx, entry)
            results.append(entry_result)
            if entry_result.status != "fail":
                total_entries += 1

    if not results:
        results.append(CheckResult(
            "hooks.yaml present + valid",
            "ok",
            f"{path} parses; no hook entries declared",
        ))
    else:
        # If every result is ok, prepend a summary line.
        if all(r.status == "ok" for r in results):
            results.insert(0, CheckResult(
                "hooks.yaml present + valid",
                "ok",
                f"{total_entries} hook entry(ies) across {len(hooks)} event(s)",
            ))
    return results


def _validate_hook_entry(event: str, idx: int, entry: Any) -> CheckResult:
    label = f"hooks.{event}[{idx}]"
    if not isinstance(entry, dict):
        return CheckResult(
            label,
            "fail",
            f"entry must be a mapping; got {type(entry).__name__}",
            remediation="Each hook entry is a YAML mapping with at minimum `kind:`.",
        )
    kind = entry.get("kind")
    if not isinstance(kind, str) or not kind:
        return CheckResult(
            label,
            "fail",
            "entry missing or empty `kind`",
            remediation=f"Set `kind:` to one of: {', '.join(HOOK_KIT_KINDS)}.",
        )
    if kind not in HOOK_KIT_KINDS:
        return CheckResult(
            label,
            "fail",
            f"unknown kind {kind!r}",
            remediation=(
                f"Known kinds at v1: {', '.join(HOOK_KIT_KINDS)}. "
                "Custom behaviour goes through `kind: custom-script` per DEC-024."
            ),
        )
    # Per-kind required-fields check (lightweight; full JSON-schema
    # validation lives in the engine at fire-time as a safety net).
    if kind == "set-board-field":
        if not entry.get("field_id"):
            return CheckResult(label, "fail", "missing `field_id`")
        if not (entry.get("single_select_option_id") or entry.get("text_value")):
            return CheckResult(
                label, "fail",
                "set-board-field requires `single_select_option_id` or `text_value`"
            )
    elif kind == "post-comment":
        tp = entry.get("template_path")
        if not isinstance(tp, str) or not tp.startswith("project/"):
            return CheckResult(
                label, "fail",
                "post-comment `template_path` must be a path under `project/`",
            )
    elif kind == "assign-milestone":
        if not entry.get("title"):
            return CheckResult(label, "fail", "assign-milestone missing `title`")
    elif kind == "custom-script":
        sp = entry.get("script_path")
        if not isinstance(sp, str) or not sp.startswith("project/"):
            return CheckResult(
                label, "fail",
                "custom-script `script_path` must be a path under `project/`",
            )
    return CheckResult(label, "ok", f"kind={kind}")


# ----- path resolution -----------------------------------------------


def _resolve_capability_root(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_dir() else None
    # Walk up from CWD looking for .pkit/capabilities/project-management.
    cur = Path.cwd()
    while cur != cur.parent:
        candidate = cur / ".pkit" / "capabilities" / CAPABILITY_NAME
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return None


# ----- review: block validation (DEC-027 + DEC-028) ------------------


def _check_review_block(
    config: dict[str, Any], capability_root: Path
) -> list[CheckResult]:
    """Validate the optional `review:` block.

    DEC-027 fields: review.mode (agent|human), review.human_review.reviewer_role.
    DEC-028 fields: review.agents.remote_registered, review.agents.local_registered.
    """
    review = config.get("review")
    if review is None:
        return [CheckResult(
            "review: block",
            "skip",
            "no `review:` block configured (defaults: mode=agent, no agents registered)",
        )]
    if not isinstance(review, dict):
        return [CheckResult(
            "review: block valid",
            "fail",
            "`review:` is present but not a mapping",
            remediation="Make `review:` a YAML mapping. See DEC-027 / DEC-028.",
        )]

    results: list[CheckResult] = []

    # DEC-027: mode + human_review.reviewer_role.
    mode = review.get("mode")
    if mode is not None and mode not in ("agent", "human"):
        results.append(CheckResult(
            "review.mode valid",
            "fail",
            f"`review.mode` must be 'agent' or 'human'; got {mode!r}",
        ))
    elif mode in ("agent", "human"):
        results.append(CheckResult("review.mode", "ok", f"mode={mode}"))

    human_review = review.get("human_review")
    if human_review is not None:
        if not isinstance(human_review, dict):
            results.append(CheckResult(
                "review.human_review valid",
                "fail",
                "`review.human_review` must be a mapping",
            ))
        else:
            role = human_review.get("reviewer_role")
            if role is not None and (not isinstance(role, str) or not role):
                results.append(CheckResult(
                    "review.human_review.reviewer_role valid",
                    "fail",
                    "`reviewer_role` must be a non-empty string when set",
                ))

    # DEC-028 + DEC-032: agents block.
    agents = review.get("agents")
    if agents is not None:
        if not isinstance(agents, dict):
            results.append(CheckResult(
                "review.agents valid",
                "fail",
                "`review.agents` must be a mapping",
            ))
        else:
            repo_root = capability_root.parent.parent.parent
            results.extend(_check_review_agents(agents, repo_root))

    if not results:
        results.append(CheckResult(
            "review: block valid", "ok", "review block parses cleanly (empty)",
        ))
    return results


def _check_review_agents(
    agents: dict[str, Any], repo_root: Path
) -> list[CheckResult]:
    """Validate `review.agents` shape and the *resolvable* reviewer set.

    Two concerns, per DEC-032's D3 (cap lift) + Implications:

      1. **Shape** of the static `remote_registered` / `local_registered`
         lists. `local_registered` no longer caps at one entry — N≥2 local
         reviewers is valid (the singleton cap lifted with DEC-032). The
         `remote_registered` path is still one entry at v1: DEC-032 D2 scopes
         *contributed* reviewers to the local path, so the multi-reviewer
         extension only landed there; the remote-bot path is unchanged.

      2. **Resolvable set.** Every name in (baseline `local_registered` ∪
         every reviewer a manifest-registered capability contributes) must
         correspond to a deployed agent file. A missing one is an
         unsatisfiable merge gate — surfaced here with remediation rather
         than left to fail mid-PR (DEC-032 D5). The contributed half is
         collected by the shared DEC-032 collector (reused, not
         re-implemented), whose own `ContributionError`s (malformed
         declaration, undeployed agent) are surfaced through this check too.
    """
    results: list[CheckResult] = []

    # 1a. remote_registered — still singleton at v1 (D2: no remote
    #     contributions). Shape-validate the single optional entry.
    results.extend(_check_remote_registered(agents.get("remote_registered")))

    # 1b. local_registered — shape-validate every entry (N≥2 allowed),
    #     collecting the baseline reviewer names for the resolvable set.
    baseline_names, local_results = _check_local_registered(
        agents.get("local_registered")
    )
    results.extend(local_results)

    # 2. Resolvable set: baseline ∪ contributed, each name → deployed file.
    results.extend(_check_resolvable_reviewer_set(baseline_names, repo_root))

    return results


def _check_remote_registered(entries: Any) -> list[CheckResult]:
    """Validate the optional `remote_registered` list (singleton at v1)."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        return [CheckResult(
            "review.agents.remote_registered valid",
            "fail",
            "`review.agents.remote_registered` must be a list",
        )]
    if len(entries) > 1:
        return [CheckResult(
            "review.agents.remote_registered singleton",
            "fail",
            f"v1 supports at most one remote entry; got {len(entries)}",
            remediation=(
                "DEC-032 lifts the local-path cap only — contributed reviewers "
                "register on the local path. Keep at most one entry in "
                "`remote_registered` at v1."
            ),
        )]
    if not entries:
        return []
    entry = entries[0]
    if not isinstance(entry, dict):
        return [CheckResult(
            "review.agents.remote_registered[0] shape",
            "fail",
            "entry must be a mapping",
        )]
    login = entry.get("github_login")
    if not isinstance(login, str) or not login:
        return [CheckResult(
            "review.agents.remote_registered[0].github_login",
            "fail",
            "`github_login` must be a non-empty string",
        )]
    return [CheckResult(
        "review.agents.remote_registered", "ok", f"github_login={login}",
    )]


def _check_local_registered(entries: Any) -> tuple[list[str], list[CheckResult]]:
    """Shape-validate `local_registered` (N≥2 allowed) and collect names.

    Returns the baseline reviewer names (the well-formed `name` of each
    entry) plus a list of shape-validation results. The names feed the
    resolvable-set check; a malformed entry contributes a `fail` result and
    no name (the resolvable-set check stays meaningful even when one entry
    is broken).
    """
    if entries is None:
        return [], []
    if not isinstance(entries, list):
        return [], [CheckResult(
            "review.agents.local_registered valid",
            "fail",
            "`review.agents.local_registered` must be a list",
        )]

    names: list[str] = []
    results: list[CheckResult] = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            results.append(CheckResult(
                f"review.agents.local_registered[{idx}] shape",
                "fail",
                "entry must be a mapping",
            ))
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            results.append(CheckResult(
                f"review.agents.local_registered[{idx}].name",
                "fail",
                "`name` must be a non-empty string",
            ))
            continue
        names.append(name)

    if names:
        results.append(CheckResult(
            "review.agents.local_registered shape",
            "ok",
            f"{len(names)} baseline local reviewer(s): {', '.join(names)}",
        ))
    return names, results


def _check_resolvable_reviewer_set(
    baseline_names: list[str], repo_root: Path
) -> list[CheckResult]:
    """Validate every name in the resolvable set has a deployed agent file.

    The resolvable set is the baseline `local_registered` names unioned with
    every reviewer name a manifest-registered capability contributes
    (DEC-032 D1/D3). A name with no deployed agent file is an unsatisfiable
    merge gate: surfaced as a `fail` with redeploy/uninstall remediation, not
    a silent pass. The contributed half — and any malformed-declaration /
    undeployed-agent problem the collector finds — comes from the shared
    DEC-032 collector, gated on its `ok` / `has_blocking_errors` channel.
    """
    results: list[CheckResult] = []

    collection = collect_contributions(repo_root)

    # Surface the collector's own structured errors (malformed declaration,
    # parse error, undeployed contributed agent). Each is blocking per the
    # collector's contract; report one fail per error so remediation is
    # specific.
    for error in collection.errors:
        scope = (
            f"capability `{error.capability}`"
            if error.capability
            else "contribution manifest"
        )
        results.append(CheckResult(
            f"review contribution ({scope})",
            "fail",
            str(error),
            remediation=(
                "Fix the capability's review-contributions declaration, "
                "redeploy its reviewer agent, or uninstall the capability. "
                "See DEC-032."
            ),
        ))

    # Build the resolvable set: baseline ∪ contributed reviewer names. A
    # contributed rule the collector already flagged undeployed
    # (deployed=False) is reported via the error channel above — exclude it
    # here to avoid a duplicate fail. Its name is still validated if the
    # baseline registers it too, since that's a separate (baseline) concern.
    contributed_names = [
        rule.reviewer for rule in collection.rules if rule.deployed
    ]
    seen: set[str] = set()
    resolvable: list[str] = []
    for name in [*baseline_names, *contributed_names]:
        if name not in seen:
            seen.add(name)
            resolvable.append(name)

    if not resolvable:
        results.append(CheckResult(
            "resolvable reviewer set",
            "skip",
            "no local reviewers registered or contributed",
        ))
        return results

    missing: list[str] = []
    for name in resolvable:
        if not agent_is_deployed(repo_root, name):
            missing.append(name)

    if missing:
        for name in missing:
            agent_file = agent_deploy_path(repo_root, name)
            results.append(CheckResult(
                f"resolvable reviewer `{name}` deployed",
                "fail",
                f"agent file not found at {agent_file}",
                remediation=(
                    f"Either remove `{name}` from the reviewer set (drop it "
                    "from `local_registered`, or uninstall the capability "
                    "contributing it) or deploy the agent at "
                    f"`.claude/agents/{name}.md`."
                ),
            ))
    else:
        results.append(CheckResult(
            "resolvable reviewer set deployed",
            "ok",
            f"all {len(resolvable)} reviewer(s) have deployed agent files: "
            f"{', '.join(resolvable)}",
        ))

    return results


if __name__ == "__main__":
    sys.exit(main())
