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
#   - the diff-scoped checks — migration coverage, the friction change check,
#     software-analysis' number check (a use case or journey number the base
#     took first), the documentation check (project-management's
#     `check-doc-mapping`, the obligations of the doc-check point against the
#     diff) and the changelog lint read a base ref and answer about the CHANGE,
#     not the tree. They are not validators and stay their own lines; a
#     capability's line is here because that capability is installed here.
#
# Runs every check (does not stop at the first failure) and reports a summary,
# so one run surfaces all problems. Exits non-zero if any check failed.
#
# Scope note: ruff + pyright are configured in pyproject.toml but the tree does
# not yet pass them (hundreds of findings); adopting them is a separate cleanup
# and they are deliberately NOT gated here yet.

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

# The diff-scoped checks (migration coverage, friction, analysis numbers, doc
# check) each read their base themselves, one way (COR-054): $PKIT_CHECK_BASE
# when it is set — CI sets it to the pull request's target — else the project's
# default branch, as `pkit repository base` shows it. So no line here passes
# --base: every line exercises the rule a contributor's own run does.

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

# The test step (#1182). The suite runs in parallel workers (pytest-xdist):
# `-n auto`, or as many as $PKIT_TEST_WORKERS names (`0` runs it in this one
# process). The tests marked `serial` cannot share the machine with other
# workers; they run after the parallel pass, in one process, in the same step.
#
# At most two full suites run at once on a machine. The step first takes one of
# two slots under the user's cache directory, and a run that finds both taken
# waits and says whose runs it waits for. A slot is an flock(2) lock: macOS has
# no `flock` command, so Python's `fcntl.flock` takes it on a descriptor this
# shell holds open, and the lock stays with this shell until the step closes
# the descriptor or the run ends, killed included. The limit is a courtesy
# between runs, not a check: when the slots cannot be opened (a read-only cache
# directory, a sandbox) or taken, the step says so and runs without it.
test_slot_dir="${XDG_CACHE_HOME:-$HOME/.cache}/pkit"

take_test_slot() {
  if ! { mkdir -p "${test_slot_dir}" &&
         exec 8<>"${test_slot_dir}/test-slot-1.lock" &&
         exec 9<>"${test_slot_dir}/test-slot-2.lock"; } 2>/dev/null; then
    echo "cannot open the test slots in ${test_slot_dir}; running without the two-suite limit"
    return
  fi
  uv run --quiet python - "$$" "${PWD}" "${test_slot_dir}" <<'PY'
import datetime
import fcntl
import os
import signal
import sys
import time

signal.signal(signal.SIGINT, signal.SIG_DFL)  # Ctrl-C while waiting ends the run, quietly
pid, checkout, slot_dir = sys.argv[1:]
SLOTS = (8, 9)  # the descriptors check.sh holds open on test-slot-1.lock and test-slot-2.lock


def take():
    """The number of the slot this run took, or None when both are taken."""
    for number, fd in enumerate(SLOTS, 1):
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            continue
        holder = f"pid {pid} in {checkout}, since {datetime.datetime.now():%H:%M:%S}"
        os.ftruncate(fd, 0)
        os.pwrite(fd, holder.encode(), 0)
        return number
    return None


if take() is None:
    print("waiting for a test slot: at most two full suites run at once on this machine,")
    print("and these two are running:")
    for fd in SLOTS:
        holder = os.pread(fd, 512, 0).decode(errors="replace").strip()
        print(f"  {holder or 'a run that has not said who it is yet'}")
    print(f"(the slots are the lock files in {slot_dir})", flush=True)
    waited = time.monotonic()
    while (number := take()) is None:
        time.sleep(2)
    print(f"took test slot {number} after {round(time.monotonic() - waited)}s", flush=True)
PY
  case $? in
    0) ;;
    130) exit 130 ;;  # interrupted while waiting
    *) echo "could not take a test slot; running without the two-suite limit" ;;
  esac
}

free_test_slot() {
  exec 8>&- 9>&-
}

run_tests() {
  local failed=0
  take_test_slot
  uv run pytest -q -n "${PKIT_TEST_WORKERS:-auto}" -m "not serial" || failed=1
  echo
  echo "-- the tests marked serial, in one process"
  # Exit 5 is pytest's "no tests collected": no test is marked serial.
  uv run pytest -q -m serial
  case $? in 0 | 5) ;; *) failed=1 ;; esac
  free_test_slot
  return "${failed}"
}

# The query commands `pkit validate` runs offline are provisioned by `pkit sync`
# (the lifecycle README, "How dependencies are provisioned before an offline
# run") — which CI runs on checkout, and a clone runs once — not by this gate.
run "tests"              run_tests
run "validate"           uv run pkit validate
run "migrations check"   uv run pkit migrations check-diff
run "friction check"     uv run pkit friction check
run "analysis numbers"   uv run pkit analysis check-numbers
run "doc check"          uv run pkit pm check-doc-mapping
run "changelog lint"     uv run pkit release lint

echo
if [ "${fail}" -ne 0 ]; then
  echo "✗ checks FAILED"
  exit 1
fi
echo "✓ all checks passed"
