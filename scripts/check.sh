#!/usr/bin/env bash
#
# The project-kit check aggregator — the single source of truth for "what must
# pass before this lands". Run by the local pre-push hook (.githooks/pre-push)
# AND by CI (.github/workflows/checks.yml), so the gate can't drift between the
# two. Add a check here once and both pick it up.
#
# The hook runs it whole, on one machine. CI runs a full run as three parts side
# by side, which this script defines (ADR-078): two slices of the suite's
# parallel pass, `--shard 1/2` and `--shard 2/2`, and the remainder, `--rest`.
# A job before them decides the form and pins the base, and one job named
# `checks` passes only when every part said that it passed.
#
# The code's own checks come first: ruff's lint (`ruff check`) and layout
# (`ruff format --check`) under the house style `pyproject.toml` settles
# (#840), then the type check, then the test suite.
#
# The type check (PRJ-010) is `scripts/pyright_ratchet.py`, which runs pyright
# once as `pyproject.toml`'s `[tool.pyright]` table sets it: the package (`src/`)
# in strict mode, everything else in standard mode. Outside the package any
# finding fails. The package is held by a ratchet: its findings, counted per
# file and rule, may not exceed the committed baseline,
# `scripts/pyright-baseline.txt`; a count below it passes and the step names the
# entries to lower (`uv run python scripts/pyright_ratchet.py lower`, from a
# committed tree). The step also refuses suppressions and file comments that
# step around the count and a configuration that narrows the package, and fails
# when the baseline's total for a rule rose against the base unless the change
# alters the lock or the pyright table — reading the base as the diff-scoped
# checks below do. CONTRIBUTING.md, "Running checks", has the rules.
#
# Then two kinds of line, deliberately apart (COR-055 point 2; ADR-058):
#
#   - `pkit validate` — the project's one check of its own STATE against the
#     invariants its records own (COR-055): the backbone's registered members
#     (manifests, schemas, configuration, packages, connections, versions,
#     decisions, friction, rule-sets, refs, process, data) and each installed
#     capability's. One line, so nothing registered can be forgotten here; it
#     fails on errors only.
#   - the diff-scoped checks — migration coverage, the numbering check of
#     decision records (a point renumbered, reused or dropped, or a point or
#     record id the base took first: `pkit decisions check-diff`, COR-058 point
#     8), the friction change check, the prose lint (the mechanical parts of
#     the writing rules, in the text the change adds: `scripts/prose_lint.py`,
#     #1415), software-analysis' number check (a use case or journey number the
#     base took first), its pointer check (a commit off the default branch,
#     named by a planned revalidation record the change adds — the base says
#     only which records are new), the documentation check (project-management's
#     `check-doc-mapping`, the obligations of the doc-check point against the
#     diff) and the changelog lint read a base ref and answer about the CHANGE,
#     not the tree. They are not validators and stay their own lines; a
#     capability's line is here because that capability is installed here.
#
# Three more lines are project-kit's own and neither kind:
#
#   - the deployed agents' check (`scripts/check_deployed_agents.py`, #1559).
#     Each tracked copy under `.claude/agents/` must be what `deploy-agents.sh`
#     writes from its source. It reads git's index, not the working tree,
#     because CI's `pkit sync` redeploys the working tree's copies before this
#     aggregator runs.
#   - the pages' console fences, run by the doc-examples capability's run
#     (`.pkit/capabilities/doc-examples/scripts/run-examples.py`, #2098). Each
#     `console` fence of a living-docs page is run as a test, in a scratch
#     project outside the repository that project-kit's setup step builds, and
#     its output compared with the page's (doc-examples DEC-001). The run is a
#     program started by its path, never a `pkit` command (DEC-001 point 9).
#   - the pages' contents lists (`scripts/page_contents.py`, #2053). A page that
#     holds the contents markers lists its second-level sections between them,
#     and a stale list fails; `--update` writes it.
#
# Runs every check (does not stop at the first failure) and reports a summary,
# so one run surfaces all problems. Exits non-zero if any check failed.
#
# `--short` runs the short check (ADR-067): every line but the test suite, and of
# the suite only the tests marked `answers`, which read the repository's own
# answers. CI runs it on a pull request whose only changes since its most recent
# full run, which passed, are answers (`scripts/short_check.py` decides). The
# pre-push hook passes no argument, so it always runs the whole aggregator.
#
# The parts of a full run (ADR-078 point 1). Together they are the whole run:
#
#   - `--shard i/N`, a slice, runs only the i-th of N shares of the suite's
#     parallel pass, in parallel workers, as the whole run does. The shares are
#     runs of consecutive tests, in the order pytest collects them after the
#     `serial` mark's filter, cut where the times in `tests/test_times.json`
#     balance them (`tests/slices.py`). A slice whose share holds no test fails.
#     It ends by printing its report: the digest of the tests collected, how
#     many they are, and how many its share held.
#   - `--rest`, the remainder, runs every other line, with the tests marked
#     `serial` in one process in the test step's place.
#
# Where $PKIT_TEST_REPORTS names a folder, each pass of pytest writes there what
# it ran: each test's time and the tests that failed, and a slice's cut. CI reads
# them, and keeps a slice's times for the table (tests/README.md, "Running the
# suite").

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

usage() {
  echo "usage: scripts/check.sh [--short | --rest | --shard i/N]" >&2
  exit 2
}

form=whole
shard=""
case "$#:${1:-}" in
  0:) ;;
  1:--short) form=short ;;
  1:--rest) form=rest ;;
  2:--shard)
    shard="$2"
    [[ "${shard}" =~ ^([1-9][0-9]*)/([1-9][0-9]*)$ ]] || usage
    [ "${BASH_REMATCH[1]}" -le "${BASH_REMATCH[2]}" ] || usage
    form=shard
    ;;
  *) usage ;;
esac

# The diff-scoped checks (migration coverage, record numbering, friction, the
# prose lint, analysis numbers and pointers, doc check) and the type check's guard on its
# baseline each read their base themselves, one way (COR-054): $PKIT_CHECK_BASE
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
# process). The parallel pass ends by printing its 30 slowest tests
# (`--durations=30`), in every run. The tests marked `serial` cannot share the
# machine with other workers; they run after the parallel pass, in one process,
# in the same step.
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

# The parallel pass, with what a caller adds to it. Any exit but 0 fails it.
parallel_pass() {
  uv run pytest -q -n "${PKIT_TEST_WORKERS:-auto}" --durations=30 -m "not serial" "$@"
}

# The tests marked serial, in one process. Exit 5 is pytest's "no tests
# collected": no test is marked serial, which passes.
serial_pass() {
  uv run pytest -q -m serial ${PKIT_TEST_REPORTS:+"--test-report=${PKIT_TEST_REPORTS}/serial"}
  case $? in 0 | 5) return 0 ;; *) return 1 ;; esac
}

run_tests() {
  local failed=0
  take_test_slot
  parallel_pass ${PKIT_TEST_REPORTS:+"--test-report=${PKIT_TEST_REPORTS}/parallel"} || failed=1
  echo
  echo "-- the tests marked serial, in one process"
  serial_pass || failed=1
  free_test_slot
  return "${failed}"
}

# A slice's test step: its share of the parallel pass, and nothing else. Exit 5 is
# pytest's "no tests collected", and fails here: an empty share means the filter
# or the cut went wrong (ADR-078 point 5). The slice always reports its cut, into
# a scratch folder where $PKIT_TEST_REPORTS names none.
run_slice() {
  local failed=0 scratch="" reports="${PKIT_TEST_REPORTS:-}"
  if [ -z "${reports}" ]; then
    scratch="$(mktemp -d)"
    reports="${scratch}"
  fi
  take_test_slot
  # One token each: pytest reads its own options before the suite's conftest adds
  # these, and would take a value apart from its option for a path to collect.
  parallel_pass "--shard=${shard}" "--test-report=${reports}/parallel" || failed=1
  free_test_slot
  if [ -n "${scratch}" ]; then rm -rf "${scratch}"; fi
  return "${failed}"
}

# The short check's test step: the tests marked `answers` alone, in one process.
# Exit 5 is pytest's "no tests collected": no test is marked `answers`.
run_answer_tests() {
  uv run pytest -q -m answers ${PKIT_TEST_REPORTS:+"--test-report=${PKIT_TEST_REPORTS}/answers"}
  case $? in 0 | 5) return 0 ;; *) return 1 ;; esac
}

# The query commands `pkit validate` runs offline are provisioned by `pkit sync`
# (the lifecycle README, "How dependencies are provisioned before an offline
# run") — which CI runs on checkout, and a clone runs once — not by this gate.
# A slice runs its test step alone; every other form runs every line.
if [ "${form}" = shard ]; then
  run "tests (slice ${shard} of the parallel pass)" run_slice
else
  run "lint"               uv run ruff check .
  run "format"             uv run ruff format --check .
  run "types"              uv run python scripts/pyright_ratchet.py
  case "${form}" in
    short) run "tests (the short check: only those marked answers)" run_answer_tests ;;
    rest)  run "tests (the remainder: only those marked serial)" serial_pass ;;
    *)     run "tests"     run_tests ;;
  esac
  run "validate"           uv run pkit validate
  run "deployed agents"    uv run python scripts/check_deployed_agents.py
  run "console fences"     uv run python .pkit/capabilities/doc-examples/scripts/run-examples.py
  run "contents lists"     uv run python scripts/page_contents.py
  run "migrations check"   uv run pkit migrations check-diff
  run "record numbering"   uv run pkit decisions check-diff
  run "friction check"     uv run pkit friction check
  run "prose lint"         uv run python scripts/prose_lint.py
  run "analysis numbers"   uv run pkit analysis check-numbers
  run "analysis pointers"  uv run pkit analysis check-pointers
  run "doc check"          uv run pkit pm check-doc-mapping
  run "changelog lint"     uv run pkit release lint
fi

echo
if [ "${fail}" -ne 0 ]; then
  echo "✗ checks FAILED"
  exit 1
fi
case "${form}" in
  short) echo "✓ all checks passed (the short check: the test suite was skipped, ADR-067)" ;;
  rest)  echo "✓ all checks passed (the remainder: every line but the suite's parallel pass)" ;;
  shard) echo "✓ all checks passed (slice ${shard} of the suite's parallel pass)" ;;
  *)     echo "✓ all checks passed" ;;
esac
