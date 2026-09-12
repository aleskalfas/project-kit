"""The prerequisite gate — bootstrap is mandatory before any gated pm verb (#747).

[project-management:DEC-017-prerequisites-bootstrap-migrate-discipline] names
`pre-check` "the hard gate on every pm operation" and the pm skill instructs the
agent to refuse on a non-zero exit. Nothing enforced it: no pm script called
pre-check, and `_lib.gh.load_adopter_config` returns ``{}`` for a missing config
so every reader silently fell back to ambient defaults. An un-bootstrapped
project was therefore not refused — it quietly got defaults for the substrate
map, the board flag, review mode, doc mappings and workstreams, which is the
"a check that was never configured is indistinguishable from a check that
passed" shape this capability has spent a long arc eliminating.

This module is that gate, in code.

What "bootstrapped" means (the cheap, local, honest definition)
--------------------------------------------------------------
Two local file reads, no network, no API calls, no reuse of `pre-check`'s 125
check results:

1. **A bootstrap stamp** at ``project/bootstrap-stamp.yaml`` — written by
   `bootstrap` when it completes, refreshed by `migrate`. The stamp attests the
   real event rather than inferring it from a config file's shape (a
   hand-written or half-copied config passes a shape test but proves nothing
   about whether the labels were ever provisioned).
2. **A shape-valid adopter config** — a config can be broken *after* a
   successful bootstrap, so the stamp alone is not enough. The check is derived
   from the companion ``schemas/config.schema.json`` (#691) rather than
   duplicating a key list here; see :func:`_config_shape_problem` for the
   honest statement of which subset of that schema is enforced.

Deliberately NOT checked: whether the labels still exist, whether the board
resolves, whether the host is reachable. Those cost live API calls, would make
`move-issue` refuse whenever the tracker has a bad minute, and answer a
different question — *is your setup still healthy?* — which stays `pre-check`'s
job, run deliberately or in CI. Conflating "did you set up?" with "is your setup
still healthy?" is what makes the full-pre-check gate tempting and wrong.

Why the stamp lives under ``project/`` and carries a repo identity
-----------------------------------------------------------------
The stamp is adopter state, so it lives in the capability's adopter-owned
``project/`` subtree — the one part of the tree ``pkit sync`` preserves
(``treecopy.refresh_owned_tree`` never overwrites or prunes ``project/``,
while every kit-owned path refreshes wholesale and root-level orphans are
pruned; since #812 the capability path also never *seeds* it from source). It deliberately does **not** live in the capability's
``manifest.yaml``: that file is re-stamped from scratch by
``_stamp_component_manifest`` on every install / refresh, so a stamp written
there would be erased by the next ``pkit sync``, and — because the kit source
tree carries its own ``manifest.yaml`` — an adopter would inherit the *kit's*
stamp on install. Either failure re-opens the hole this gate closes.

``project/`` has the mirror-image hazard: a stamp committed in one repo can
still arrive in another and be read as "already bootstrapped" there. Install no
longer seeds ``project/`` from source (#812, which this hazard helped motivate),
but two vectors remain — a repo started by copying another project's ``.pkit/``
tree, and any adopter still carrying a stamp seeded by a pre-#812 install. The
#814 cleanup migration deliberately REPORTS such a stamp rather than
removing it, and points the adopter here: deciding whether a stamp is
foreign needs the same normaliser that wrote it, which lives in this
module's canonicaliser, and a shell re-implementation that disagreed
would delete stamps that are legitimately the adopter's. So this
refusal stays the defence, not a stopgap awaiting cleanup. The stamp therefore records the **repo
identity** it was written for (the normalised ``origin`` URL, read locally via
git — no network) and the gate refuses when the stamp names a *different* repo
than the one it is running in. A copied or seeded stamp is inert rather than
fail-open. Honest about reach, per the same posture as
:mod:`_lib.session_guard`: when either side's identity cannot be resolved (no
git, no ``origin``), the binding does **not** fire — the gate never fabricates a
refusal it cannot back.

Exemptions (the whole list, visible in code)
--------------------------------------------
:data:`EXEMPT_VERBS` — five setup-and-diagnosis verbs, each either how you
*become* bootstrapped or how you *diagnose why you are not*. Everything else is
gated, including the read-only verbs and the engine-called predicates: a read
that assumes kit labels misreports an adopter's remapped values, and a
predicate that answers "where is this issue?" from assumed defaults is the same
silent-wrong-answer shape. A refusing predicate is correct — the engine treats
an unevaluable predicate as indeterminate and fails closed, and an
un-bootstrapped project genuinely cannot say where an issue stands. (A
warn-and-continue banner was considered and rejected: a warning printed on
every command is ignored within a week.)

The gate is called explicitly at the top of each gated entry point — not in the
dispatcher (direct script invocation, which happens constantly, would bypass
it: the exact hole) and not inside the shared config/`gh` seam (the refusal
would fire deep in the call stack, far from the command the user typed, and
exempt scripts would have to *opt out* — forget the opt-out and `bootstrap`
itself is broken). ``tests/test_pm_bootstrap_gate_coverage.py`` is the guard
that keeps the set complete: every verb registered in ``package.yaml`` either
calls the gate or appears in :data:`EXEMPT_VERBS`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # ruamel is declared by every pm script's PEP 723 header.
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # pragma: no cover — ruamel is in the kit's pyproject
    YAML = None  # type: ignore[assignment]
    YAMLError = Exception  # type: ignore[assignment,misc]

CAPABILITY_NAME = "project-management"

# Adopter-state paths, capability-root-relative.
STAMP_RELATIVE = Path("project") / "bootstrap-stamp.yaml"
CONFIG_RELATIVE = Path("project") / "config.yaml"
CONFIG_SCHEMA_RELATIVE = Path("schemas") / "config.schema.json"
PACKAGE_RELATIVE = Path("package.yaml")

# The stamp's own shape version, and its self-describing binding tag (COR-023)
# so `pkit data validate` resolves the file to `schemas/bootstrap-stamp.*`.
STAMP_SCHEMA_VERSION = 1
STAMP_BINDING = f"{CAPABILITY_NAME}:bootstrap-stamp"

# Who wrote a stamp — a diagnostic recorded in the stamp's `by:` field.
BY_BOOTSTRAP = "bootstrap"
BY_MIGRATE = "migrate"
BY_MIGRATION_GRANDFATHER = "migration-grandfather"

# The five setup-and-diagnosis verbs that must work on an un-bootstrapped
# project, each with the reason it is exempt. This mapping IS the exemption
# list: the coverage guard reads it, and a verb absent from here must call the
# gate.
EXEMPT_VERBS: dict[str, str] = {
    "bootstrap": (
        "the verb that makes a project bootstrapped — gating it would be a "
        "deadlock, and it is what writes the stamp"
    ),
    "pre-check": (
        "the diagnosis: it exists to report which prerequisites are missing, "
        "so refusing it would hide the answer the operator needs"
    ),
    "migrate": (
        "the upgrade path may legitimately precede a re-bootstrap; it also "
        "refreshes the stamp"
    ),
    "adopt-existing": (
        "brownfield inventory runs BEFORE the config exists — it is what tells "
        "the adopter what to put in it (reads only, mutates nothing)"
    ),
    "self-test": (
        "the smoke test of the capability's own transition cycle; a diagnostic "
        "of last resort that must be runnable when the project looks broken"
    ),
}


@dataclass(frozen=True)
class Stamp:
    """A parsed bootstrap stamp."""

    completed_at: str
    capability_version: str
    by: str
    repo: str | None


@dataclass(frozen=True)
class GateOutcome:
    """The verdict on "may a gated verb run in this project?"."""

    ok: bool
    # Why the gate refused (empty when ok). Written for a human reading a
    # terminal: names the missing prerequisite, not an error class.
    reason: str = ""
    stamp: Stamp | None = None
    # The capability version installed right now (from package.yaml), and
    # whether it differs from the version recorded in the stamp. Staleness is
    # *reported*, never a refusal on its own: most upgrades do not change
    # bootstrap's obligations, and refusing on every version drift would break
    # the whole capability after every upgrade until a re-bootstrap.
    installed_version: str | None = None
    stale: bool = False


# ----- the public gate ------------------------------------------------


def evaluate(capability_root: Path | None = None) -> GateOutcome:
    """Decide whether this project is bootstrapped. Local file reads only.

    ``capability_root`` is the installed capability directory; when None it is
    resolved by walking up from the CWD (the same discovery every pm script
    uses). No network, no `gh`, no API calls — the only subprocess is a local
    ``git remote get-url origin`` for the stamp's repo binding.
    """
    root = capability_root if capability_root is not None else _resolve_capability_root()
    if root is None or not root.is_dir():
        return GateOutcome(
            ok=False,
            reason=(
                f"the {CAPABILITY_NAME} capability is not installed here "
                f"(no .pkit/capabilities/{CAPABILITY_NAME}/ in this directory "
                f"or any parent)"
            ),
        )

    installed_version = _read_installed_version(root)

    stamp, stamp_problem = _read_stamp(root)
    if stamp is None:
        return GateOutcome(
            ok=False, reason=stamp_problem, installed_version=installed_version
        )

    stale = bool(
        installed_version
        and stamp.capability_version
        and installed_version != stamp.capability_version
    )

    binding_problem = _repo_binding_problem(stamp, root)
    if binding_problem is not None:
        return GateOutcome(
            ok=False,
            reason=binding_problem,
            stamp=stamp,
            installed_version=installed_version,
            stale=stale,
        )

    config_problem = _config_shape_problem(root)
    if config_problem is not None:
        return GateOutcome(
            ok=False,
            reason=config_problem,
            stamp=stamp,
            installed_version=installed_version,
            stale=stale,
        )

    return GateOutcome(
        ok=True, stamp=stamp, installed_version=installed_version, stale=stale
    )


def enforce(
    verb: str,
    *,
    capability_root: Path | None = None,
    allow_help: bool = False,
    stream=None,
) -> bool:
    """Run the gate at a gated entry point; True iff the verb may proceed.

    The single call site every gated script uses, at the top of ``main()``
    after argument parsing::

        if not bootstrap_gate.enforce("move-issue", capability_root=capability_root):
            return 2

    ``allow_help`` is for the handful of entry points that delegate their whole
    argument parsing to a shared runner (`check-criterion`, `comment-issue`, …):
    there the gate necessarily runs BEFORE argparse, so a ``--help`` invocation
    would be refused rather than answered. Setting it lets a help request
    through — printing usage performs no operation, and every other verb
    (whose argparse runs first) already answers ``--help`` un-bootstrapped.

    On refusal it prints the explanation naming *this* verb and the exact
    command that fixes it, and returns False; the caller exits non-zero (2 —
    "could not proceed", matching `migrate`'s documented "refused" code and the
    usage-error code every pm script already reserves for "did not run"). For a
    predicate, any non-zero exit is what the process engine reads as
    indeterminate, so the same code is correct there.

    Never raises: an unexpected failure inside the gate is reported and treated
    as a refusal, because a gate that cannot evaluate must not wave a command
    through — the fail-open behaviour this exists to remove.

    ``stream`` defaults to the *current* ``sys.stderr``, resolved at call time
    so test capture and stream redirection are honoured.
    """
    if stream is None:
        stream = sys.stderr
    if allow_help and is_help_request():
        return True
    try:
        outcome = evaluate(capability_root)
    except Exception as exc:  # fail CLOSED, and say why.
        print(
            refusal_message(
                verb,
                GateOutcome(
                    ok=False,
                    reason=f"the prerequisite gate could not be evaluated ({exc!r})",
                ),
            ),
            file=stream,
        )
        return False
    if outcome.ok:
        return True
    print(refusal_message(verb, outcome), file=stream)
    return False


def is_help_request(argv: list[str] | None = None) -> bool:
    """Whether this invocation is asking for usage rather than doing work."""
    args = argv if argv is not None else sys.argv[1:]
    return any(a in ("-h", "--help") for a in args)


def refusal_message(verb: str, outcome: GateOutcome) -> str:
    """The self-remedying refusal text: what is missing, and the exact fix.

    The hint is the point — the failure must be self-remedying rather than a
    puzzle — so it names both invocation forms (the dispatcher one an adopter
    types, and the direct-script one CI and agents use) and points at
    `pre-check` for the full diagnosis.
    """
    lines = [
        f"[refused] {verb}: {CAPABILITY_NAME} prerequisites are not met "
        f"(DEC-017's hard gate, in code per #747)",
        f"          → {outcome.reason}",
        "          → Until then this project cannot be operated on: every "
        "value a pm command reports or writes (classification substrate, "
        "board flag, review mode, doc mappings, workstreams) would come from "
        "assumed defaults, so the answer would be confidently wrong rather "
        "than absent.",
        "          → To fix: run `pkit " + CAPABILITY_NAME + " bootstrap`",
        f"            (direct: uv run --script .pkit/capabilities/"
        f"{CAPABILITY_NAME}/scripts/bootstrap.py)",
        f"          → For the full diagnosis of what is missing: "
        f"`pkit {CAPABILITY_NAME} pre-check`",
    ]
    if outcome.stamp is not None:
        lines.append(
            f"          → Stamp found: bootstrapped at "
            f"{outcome.stamp.completed_at} by `{outcome.stamp.by}` at "
            f"capability v{outcome.stamp.capability_version}"
            + (f" for repo {outcome.stamp.repo}" if outcome.stamp.repo else "")
        )
    return "\n".join(lines)


def staleness_note(outcome: GateOutcome) -> str | None:
    """A one-line staleness advisory, or None when the stamp is current.

    Staleness is a *signal*, not a refusal: the stamp records the capability
    version that bootstrapped, so a version whose bootstrap obligations changed
    can be detected — but most upgrades change nothing about bootstrap, and
    refusing on drift would break every command after every upgrade. The
    diagnosis surface (`pre-check`) is where this is meant to be surfaced, not
    a banner on every command.
    """
    if not outcome.stale or outcome.stamp is None:
        return None
    return (
        f"bootstrap stamp records capability v{outcome.stamp.capability_version}, "
        f"but v{outcome.installed_version} is installed — re-run "
        f"`pkit {CAPABILITY_NAME} bootstrap` (or `migrate`) if this upgrade "
        f"changed what bootstrap provisions"
    )


# ----- writing the stamp ---------------------------------------------


def stamp_path(capability_root: Path) -> Path:
    """The canonical stamp path for an installed capability."""
    return capability_root / STAMP_RELATIVE


def write_stamp(
    capability_root: Path,
    *,
    by: str,
    now: datetime | None = None,
) -> Path:
    """Write (or refresh) the bootstrap stamp; return the path written.

    Called by `bootstrap` when it completes and by `migrate` when it refreshes
    an existing stamp. Records the capability version installed at the time so
    the stamp is a staleness signal rather than a boolean, and the repo
    identity it was written for so a copied stamp is inert.

    Value-level idempotent apart from the timestamp: re-running rewrites the
    same file with a new ``completed_at``.
    """
    if YAML is None:  # pragma: no cover — ruamel is in the kit's pyproject
        raise RuntimeError("ruamel.yaml is required to write the bootstrap stamp")
    path = stamp_path(capability_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    moment = (now or datetime.now(timezone.utc)).isoformat()
    document = {
        "schema_version": STAMP_SCHEMA_VERSION,
        "pkit_schema": STAMP_BINDING,
        "bootstrap": {
            "completed_at": moment,
            "capability_version": _read_installed_version(capability_root) or "unknown",
            "by": by,
            "repo": current_repo_identity(capability_root),
        },
    }
    yaml = YAML()
    yaml.default_flow_style = False
    with path.open("w", encoding="utf-8") as handle:
        handle.write(
            "# Bootstrap completion stamp — machine-written, do NOT hand-edit.\n"
            "# Written by `bootstrap`, refreshed by `migrate`; read by the\n"
            "# prerequisite gate that every non-exempt pm verb calls (#747).\n"
            "# Deleting this file makes every gated pm verb refuse until\n"
            "# bootstrap runs again.\n"
        )
        yaml.dump(document, handle)
    return path


# ----- stamp reading -------------------------------------------------


def _read_stamp(capability_root: Path) -> tuple[Stamp | None, str]:
    """Parse the stamp, or return (None, why-this-counts-as-not-bootstrapped).

    Every deviation from the expected shape is treated as "not bootstrapped"
    rather than raising: the gate's whole purpose is that an unreadable
    prerequisite must not read as a satisfied one.
    """
    path = stamp_path(capability_root)
    if not path.is_file():
        return None, (
            f"this project has never completed `bootstrap` — no stamp at {path}"
        )
    if YAML is None:  # pragma: no cover — ruamel is in the kit's pyproject
        return None, f"cannot read {path} (ruamel.yaml unavailable)"
    try:
        raw = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError) as exc:
        return None, f"the bootstrap stamp at {path} is unreadable ({exc})"
    if not isinstance(raw, dict):
        return None, f"the bootstrap stamp at {path} is not a YAML mapping"
    block = raw.get("bootstrap")
    if not isinstance(block, dict):
        return None, (
            f"the bootstrap stamp at {path} carries no `bootstrap:` block "
            f"(it does not attest a completed bootstrap)"
        )
    completed_at = block.get("completed_at")
    version = block.get("capability_version")
    if not isinstance(completed_at, str) or not completed_at:
        return None, (
            f"the bootstrap stamp at {path} has no `bootstrap.completed_at` "
            f"timestamp (it does not attest a completed bootstrap)"
        )
    if not isinstance(version, str) or not version:
        return None, (
            f"the bootstrap stamp at {path} has no "
            f"`bootstrap.capability_version` (it does not attest which "
            f"capability version bootstrapped)"
        )
    repo = block.get("repo")
    return (
        Stamp(
            completed_at=completed_at,
            capability_version=version,
            by=str(block.get("by") or "unknown"),
            repo=repo if isinstance(repo, str) and repo else None,
        ),
        "",
    )


def _repo_binding_problem(stamp: Stamp, capability_root: Path) -> str | None:
    """Refuse a stamp that was written for a *different* repository.

    The stamp lives in the adopter-owned ``project/`` subtree, so it can arrive
    by copy — a repo started by copying another project's ``.pkit/`` tree, or an
    adopter still carrying one seeded by a pre-#812 install (installs no longer
    seed ``project/`` from source, but existing trees are not cleaned up). A
    stamp naming another repo attests nothing about *this* one.

    Fires only when BOTH identities resolve and differ — an unresolvable
    identity on either side (no git, no ``origin``) means the check cannot be
    made, and the gate does not fabricate a refusal it cannot back.
    """
    if stamp.repo is None:
        return None
    here = current_repo_identity(capability_root)
    if here is None or here == stamp.repo:
        return None
    return (
        f"the bootstrap stamp was written for a different repository "
        f"({stamp.repo}) than this one ({here}) — it was copied in rather than "
        f"earned here, so it attests nothing about this project"
    )


def current_repo_identity(start: Path | None = None) -> str | None:
    """The normalised ``origin`` identity of the repo at *start*, or None.

    A LOCAL git read (no network): ``git -C <start> remote get-url origin``,
    normalised through :mod:`_lib.session_guard`'s canonicaliser so the same
    repo cloned over ssh and https compares equal. None when git is
    unavailable, *start* is not in a repo, or there is no ``origin`` remote.

    *start* is the **capability root**, not the CWD: the stamp lives in that
    tree, so it is bound to the repo that tree belongs to. The two coincide on
    the ordinary path (the root is discovered by walking up from the CWD) and
    the distinction matters when a caller passes ``--capability-root``
    explicitly at some other location.
    """
    where = start if start is not None else Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "-C", str(where), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    return normalize_repo_identity(raw)


def normalize_repo_identity(raw: str) -> str:
    """Normalise a remote URL to a transport-independent repo identity.

    Reuses `session_guard`'s canonicaliser (COR-007: one normaliser, not two)
    with a local fallback if that import is unavailable for any reason.
    """
    try:
        # Deferred import: keeps `_lib` import order free of a cycle.
        from _lib import session_guard

        return session_guard.normalize_origin_url(raw)
    except Exception:  # never let identity normalisation crash the gate
        stripped = raw.strip().rstrip("/")
        if stripped.endswith(".git"):
            stripped = stripped[: -len(".git")]
        return stripped.casefold()


# ----- config shape --------------------------------------------------


def _config_shape_problem(capability_root: Path) -> str | None:
    """Check the adopter config's shape; None when it is acceptable.

    Enforces a deliberately-named SUBSET of the companion
    ``schemas/config.schema.json`` (#691) — the structural half that needs no
    validator dependency in 60 PEP 723 scripts:

      * the file exists, parses, and is a top-level mapping;
      * every key the companion declares ``required`` is present (the same set
        `pre-check` requires, read from the schema so the two cannot drift);
      * no top-level key the companion does not declare, when it sets
        ``additionalProperties: false`` — the check that catches the
        misspelling the schema was built for (``has_projects_v2_boards`` with a
        trailing ``s`` silently left an adopter in label-fallback mode).

    NOT enforced here: per-key types, patterns, and nested shapes. Those are
    `pkit data validate` / `pre-check`'s job — this is the gate's "is the
    config still the file bootstrap was run against?" question, not a full
    validation. When the companion schema itself is missing or unreadable the
    shape check is SKIPPED rather than failed: the capability install is
    corrupt in that case, and the gate does not claim a verdict it cannot
    derive (the stamp still gates).
    """
    path = capability_root / CONFIG_RELATIVE
    if not path.is_file():
        return (
            f"the adopter config is missing at {path} — without it every pm "
            f"command would silently fall back to ambient defaults"
        )
    if YAML is None:  # pragma: no cover — ruamel is in the kit's pyproject
        return None
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError) as exc:
        return f"the adopter config at {path} is unreadable ({exc})"
    if not isinstance(data, dict):
        return f"the adopter config at {path} is not a YAML mapping"

    schema = _load_config_schema(capability_root)
    if schema is None:
        return None  # cannot derive the shape rules; the stamp still gates.

    required = [k for k in schema.get("required", []) if isinstance(k, str)]
    missing = [k for k in required if k not in data]
    if missing:
        return (
            f"the adopter config at {path} is missing required key(s): "
            f"{', '.join(missing)}"
        )

    if schema.get("additionalProperties") is False:
        known = set(schema.get("properties", {}) or {})
        unknown = sorted(k for k in data if isinstance(k, str) and k not in known)
        if unknown:
            return (
                f"the adopter config at {path} carries unknown key(s): "
                f"{', '.join(unknown)} — a misspelled key is silently ignored "
                f"by every reader, so it is refused here"
            )
    return None


def _load_config_schema(capability_root: Path) -> dict[str, Any] | None:
    """The companion config schema as a dict, or None when unreadable."""
    path = capability_root / CONFIG_SCHEMA_RELATIVE
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


# ----- helpers -------------------------------------------------------


def _read_installed_version(capability_root: Path) -> str | None:
    """The installed capability version from ``package.yaml``, or None."""
    path = capability_root / PACKAGE_RELATIVE
    if not path.is_file() or YAML is None:
        return None
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    component = data.get("component")
    if not isinstance(component, dict):
        return None
    version = component.get("version")
    return str(version) if version else None


def _resolve_capability_root() -> Path | None:
    """Walk up from the CWD to the installed capability directory, or None.

    Duplicates `_lib.membership.resolve_capability_root`'s walk deliberately:
    the gate must be importable by every entry point (including the predicates,
    which import no other `_lib` module) without dragging in membership's
    `gh`-touching surface.
    """
    cur = Path.cwd()
    while cur != cur.parent:
        candidate = cur / ".pkit" / "capabilities" / CAPABILITY_NAME
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return None
