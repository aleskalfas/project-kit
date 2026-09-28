#!/usr/bin/env bash
#
# The project-kit check aggregator — the single source of truth for "what must
# pass before this lands". Run by the local pre-push hook (.githooks/pre-push)
# AND by CI (.github/workflows/checks.yml), so the gate can't drift between the
# two. Add a check here once and both pick it up.
#
# Two kinds of line, deliberately apart (ADR-058):
#
#   - `pkit validate` — the one umbrella over every check of the tree's STATE:
#     the backbone's registered members (manifests, schemas, configuration,
#     packages, connections, versions, friction, rule-sets, decisions, refs,
#     process, data) and each installed capability's. One line, so nothing
#     registered can be forgotten here; it fails on errors only.
#   - the diff-scoped checks — migration coverage, the friction change check
#     and the changelog lint read a base ref and answer about the CHANGE, not
#     the tree. They are not validators and stay their own lines.
#
# Runs every check (does not stop at the first failure) and reports a summary,
# so one run surfaces all problems. Exits non-zero if any check failed.
#
# Scope note: ruff + pyright are configured in pyproject.toml but the tree does
# not yet pass them (hundreds of findings); adopting them is a separate cleanup
# and they are deliberately NOT gated here yet.

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

# Base ref for the diff-scoped checks (migration coverage, friction). CI
# overrides via env for PRs; locally it defaults to the tracked main.
BASE="${PKIT_CHECK_BASE:-origin/main}"

fail=0
run() {
  local label="$1"; shift
  echo
  echo "== ${label} =="
  if "$@"; then
    echo "-- ${label}: ok"
  else
    echo "-- ${label}: FAILED"
    fail=1
  fi
}

run "tests"              uv run pytest -q
run "validate"           uv run pkit validate
run "migrations check"   uv run pkit migrations check-diff --base "${BASE}"
run "friction check"     uv run pkit friction check --base "${BASE}"
run "changelog lint"     uv run pkit release lint

echo
if [ "${fail}" -ne 0 ]; then
  echo "✗ checks FAILED"
  exit 1
fi
echo "✓ all checks passed"
