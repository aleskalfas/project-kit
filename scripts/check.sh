#!/usr/bin/env bash
#
# The project-kit check aggregator — the single source of truth for "what must
# pass before this lands". Run by the local pre-push hook (.githooks/pre-push)
# AND by CI (.github/workflows/checks.yml), so the gate can't drift between the
# two. Add a check here once and both pick it up.
#
# Runs every check (does not stop at the first failure) and reports a summary,
# so one run surfaces all problems. Exits non-zero if any check failed.
#
# Scope note: ruff + pyright are configured in pyproject.toml but the tree does
# not yet pass them (hundreds of findings); adopting them is a separate cleanup
# and they are deliberately NOT gated here yet.

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

# Base ref for the migration-coverage diff. CI overrides via env for PRs;
# locally it defaults to the tracked main.
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
run "schemas validate"   uv run pkit schemas validate
run "decisions validate" uv run pkit decisions validate
run "migrations check"   uv run pkit migrations check-diff --base "${BASE}"
run "changelog lint"     uv run pkit release lint

echo
if [ "${fail}" -ne 0 ]; then
  echo "✗ checks FAILED"
  exit 1
fi
echo "✓ all checks passed"
