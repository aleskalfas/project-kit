"""The parts of the required check in CI, and the verdict of `checks` over them (ADR-078).

`.github/workflows/checks.yml` runs a full run of the aggregator as three parts side
by side, each a job of its own: two slices of the suite's parallel pass, and the
remainder. A job before them decides the form and pins the base. In the short form
the remainder's job runs the short check, and no slice starts. One job named
`checks` runs last and judges them all.

**A part,** `run`, runs `scripts/check.sh` with the part's argument, `--shard i/N`,
`--rest` or `--short`, and then:

- **times itself,** and hands the time on as the output `seconds`;
- **names its failures** in its job's summary: each failing line of the
  aggregator, and each failing test, read from the reports pytest wrote under
  `$PKIT_TEST_REPORTS` (`tests/slices.py`). A slice also says which slice it is,
  and how to run it again;
- **a slice reports its cut,** as the outputs `digest`, `collected`, `share`,
  `listed` and `unlisted`. Its share is the number of tests pytest reported on;
- **says that it passed,** as the output `passed`, last and only once the part
  passed. The output names what it attests: `check.sh --shard i/N <digest>`,
  `check.sh --rest` or `check.sh --short`.

**The verdict,** `verdict full|short`, is the step of `checks` that holds that form.
It reads every job's outcome and outputs from `$PKIT_NEEDS`, the workflow's
`needs` context as JSON, and passes only where every part the form requires ended
in success and said that it passed:

- **full:** the deciding job named a form, the remainder attests `--rest`, and each
  slice attests its own slice and digest. The slices agree: one digest, one number
  collected, and shares that add up to it;
- **short:** a pull request's deciding job named the short form, and the remainder
  attests `--short`. The slices are not required;
- **on a pull request,** in both forms, the changeset guard also said it passed.

Its summary says which form ran, lists each part with how it ended and how long it
took, and whether the slices agree. It warns where the slices collected a tenth
fewer tests than the table names, and says how many tests collected the table
lacks. It copies no part's failures. Where the decider gave no answer, it says that
the run is full, and how the deciding step ended (ADR-067 point 9).

    python scripts/ci_parts.py run --shard 1/2
    python scripts/ci_parts.py verdict full --slices 2

It needs only Python's standard library, so `checks` runs it with no project set up.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check.sh"
DESCRIPTION = "The parts of the required check in CI, and the verdict of checks over them."

FULL, SHORT = "full", "short"
PULL_REQUEST = "pull_request"

#: The jobs of the workflow, by their ids. The slices are `slice-1` to `slice-N`.
DECIDE, REST = "decide", "rest"
SLICE = "slice-{}"

#: What the changeset guard's output says once it passed.
GUARD = "changeset guard"

#: How many failing tests a part's summary names before it counts the rest.
NAMED = 50

#: The line the aggregator prints for a check that failed.
_FAILED_LINE = re.compile(r"-- (.+): FAILED")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def attests(part: Sequence[str], digest: str = "") -> str:
    """What a part's `passed` output says: its argument to the aggregator, and a slice's
    digest."""
    return " ".join(["check.sh", *part, *([digest] if digest else [])])


def slice_name(index: int, count: int) -> str:
    return f"slice {index} of {count}"


# --- a part ---------------------------------------------------------------------------


@dataclass
class Report:
    """What a part's reports say: a slice's cut, and the tests that failed."""

    cut: Mapping[str, Any] | None = None
    share: int | None = None
    failed: list[str] = field(default_factory=lambda: [])


def read_reports(reports: Path) -> Report:
    """The reports pytest wrote under `reports`, one folder for each pass."""
    found = Report()
    for ran in sorted(reports.glob("*/ran.json")):
        said = _json(ran)
        found.failed += [str(test) for test in said.get("failed") or []]
        if ran.parent.name == "parallel":
            found.share = len(cast("Mapping[str, Any]", said.get("tests") or {}))
    cut = reports / "parallel" / "cut.json"
    if cut.is_file():
        found.cut = _json(cut)
    return found


def _json(path: Path) -> Mapping[str, Any]:
    try:
        said = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return cast("Mapping[str, Any]", said) if isinstance(said, Mapping) else {}


def part_outputs(part: Sequence[str], seconds: int, report: Report) -> dict[str, str]:
    """The outputs a part hands on, but `passed`. A value from the slice's report is
    handed on only in its form, a digest as `_DIGEST` writes it and a count in digits,
    and is empty otherwise: what the report holds never writes a line of its own into
    `$GITHUB_OUTPUT`, and a slice whose digest is empty did not pass."""
    outputs = {"seconds": str(seconds)}
    if part[0] == "--shard" and report.cut is not None:
        digest = str(report.cut.get("digest", ""))
        outputs["digest"] = digest if _DIGEST.fullmatch(digest) else ""
        for key in ("collected", "listed", "unlisted"):
            count = report.cut.get(key)
            outputs[key] = str(count) if _count_form(count) else ""
        outputs["share"] = "" if report.share is None else str(report.share)
    return outputs


def _count_form(value: object) -> bool:
    """A count as a slice's report writes it: a whole number, not below zero."""
    return (isinstance(value, int) and not isinstance(value, bool) and value >= 0) or (
        isinstance(value, str) and value.isascii() and value.isdigit()
    )


def part_summary(
    part: Sequence[str], passed: bool, seconds: int, lines: Sequence[str], report: Report
) -> str:
    """The part's own section of its job's summary: how it ended, and each failure."""
    if part[0] == "--shard":
        index, count = (int(n) for n in part[1].split("/"))
        title = f"{slice_name(index, count)} of the suite's parallel pass"
    elif part[0] == "--rest":
        title = "the remainder: every line but the suite's parallel pass"
    else:
        title = "the short check: the aggregator without its test suite"
    ended = "passed" if passed else "did not pass"
    out = [f"### `{attests(part)}`, {title}: {ended}", "", f"It took {duration(seconds)}."]
    if report.cut is not None:
        cut = report.cut
        out += [
            "",
            f"Its share held {_count(report.share)} of the {_count(cut.get('collected'))} "
            f"tests collected, digest {_code(str(cut.get('digest')))}.",
        ]
    if lines:
        out += ["", "The lines of the aggregator that failed:", ""]
        out += [f"- {_code(line)}" for line in lines]
    if report.failed:
        out += ["", f"The tests that failed ({len(report.failed)}):", ""]
        out += [f"- {_code(test)}" for test in report.failed[:NAMED]]
        if len(report.failed) > NAMED:
            out.append(f"- and {len(report.failed) - NAMED} more, in the step's log")
    if not passed:
        out += ["", f"Run it again: {_code('./scripts/check.sh ' + ' '.join(part))}."]
    return "\n".join(out) + "\n"


def run_part(part: Sequence[str], env: Mapping[str, str], check: Path = CHECK) -> int:
    """Run the aggregator's part, hand on its outputs, `passed` last where it passed,
    and name its failures in the job's summary."""
    reports = Path(env["RUNNER_TEMP"]) / "test-reports"
    started = time.monotonic()
    lines: list[str] = []
    with subprocess.Popen(
        [str(check), *part],
        env={**env, "PKIT_TEST_REPORTS": str(reports)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            failed = _FAILED_LINE.fullmatch(line.rstrip("\n"))
            if failed:
                lines.append(failed[1])
        status = proc.wait()
    seconds = round(time.monotonic() - started)
    report = read_reports(reports)
    outputs = part_outputs(part, seconds, report)
    passed = status == 0
    digest = ""
    if part[0] == "--shard":
        # A slice that passed but reported no cut, or no test it ran, did not pass.
        digest, share = outputs.get("digest", ""), outputs.get("share", "")
        ran = share.isdigit() and int(share) > 0
        passed = passed and bool(_DIGEST.fullmatch(digest)) and ran
    _append(env, "GITHUB_STEP_SUMMARY", part_summary(part, passed, seconds, lines, report))
    _append(env, "GITHUB_OUTPUT", "".join(f"{k}={v}\n" for k, v in outputs.items()))
    if not passed:
        return status or 1
    _append(env, "GITHUB_OUTPUT", f"passed={attests(part, digest)}\n")
    return 0


# --- the verdict ------------------------------------------------------------------------


@dataclass
class Job:
    """A job as `needs` holds it: how it ended, and its outputs."""

    result: str
    outputs: Mapping[str, str]


def job(needs: Mapping[str, Any], name: str) -> Job:
    found = needs.get(name)
    if not isinstance(found, Mapping):
        return Job("missing", {})
    held = cast("Mapping[str, Any]", found)
    outputs = held.get("outputs")
    outputs = cast("Mapping[str, Any]", outputs) if isinstance(outputs, Mapping) else {}
    return Job(str(held.get("result") or "missing"), {k: str(v) for k, v in outputs.items()})


@dataclass
class Verdict:
    passed: bool
    summary: str


#: A row of the summary's table: the part, how its job ended, how long it took, and
#: what it said.
Row = tuple[str, str, str, str]


def verdict(form: str, slices: int, needs: Mapping[str, Any], event: str) -> Verdict:
    """Whether `checks` passes in `form`, and its summary."""
    wrong: list[str] = []
    warned: list[str] = []
    rows: list[Row] = []
    decide = job(needs, DECIDE)
    named = decide.outputs.get("form", "")
    rows.append(("deciding the form", decide.result, "", f"named {_code(named)}" if named else ""))
    if decide.result != "success" or named not in (FULL, SHORT):
        wrong.append(f"the deciding job named no form (it ended in {_code(decide.result)})")
    if form == SHORT and event != PULL_REQUEST:
        wrong.append("only a pull request may take the short form")
    if form == SHORT and named != SHORT:
        wrong.append("the deciding job did not name the short form")

    if form == FULL:
        found: list[Job] = []
        for index in range(1, slices + 1):
            part = job(needs, SLICE.format(index))
            found.append(part)
            name = slice_name(index, slices)
            digest = part.outputs.get("digest", "")
            share = part.outputs.get("share", "")
            rows.append((name, part.result, _took(part), f"ran {_count(share)}" if share else ""))
            expected = attests(["--shard", f"{index}/{slices}"], digest)
            _judge(wrong, name, part, expected if _DIGEST.fullmatch(digest) else None)
        _agree(wrong, warned, found)

    rest = job(needs, REST)
    part_arg = "--rest" if form == FULL else "--short"
    said = rest.outputs.get("passed", "")
    rows.append(("the remainder", rest.result, _took(rest), _code(said) if said else ""))
    _judge(wrong, "the remainder", rest, attests([part_arg]))

    if event == PULL_REQUEST:
        guard = rest.outputs.get("guard", "")
        rows.append(("the changeset guard", rest.result, "", _code(guard) if guard else ""))
        if guard != GUARD:
            wrong.append(f"the changeset guard did not say it passed (it said {_code(guard)})")

    return Verdict(not wrong, _summary(form, decide, rows, wrong, warned))


def _judge(wrong: list[str], name: str, part: Job, expected: str | None) -> None:
    """A part passes where its job ended in success and it says it passed what it should."""
    if part.result != "success":
        wrong.append(f"{name} ended in {_code(part.result)}")
        return
    said = part.outputs.get("passed", "")
    if expected is None or said != expected:
        wrong.append(f"{name} did not say that it passed what it should (it said {_code(said)})")


def _agree(wrong: list[str], warned: list[str], slices: Sequence[Job]) -> None:
    """The slices agree: one digest, one number collected, and shares that add up to it.
    Warns where collection fell a tenth below the table, and says what the table lacks."""
    digests = {part.outputs.get("digest", "") for part in slices}
    collected = {part.outputs.get("collected", "") for part in slices}
    shares = [part.outputs.get("share", "") for part in slices]
    if len(digests) != 1 or "" in digests:
        wrong.append("the slices do not report one digest, so they did not cut the same tests")
        return
    if len(collected) != 1 or not all(n.isdigit() for n in [*collected, *shares]):
        wrong.append("the slices do not report one number of tests collected, and each share")
        return
    (total,) = (int(n) for n in collected)
    ran = sum(int(n) for n in shares)
    if ran != total:
        wrong.append(f"the slices ran {_count(ran)} tests, not the {_count(total)} collected")
    first = slices[0].outputs
    listed, unlisted = first.get("listed", ""), first.get("unlisted", "")
    if listed.isdigit() and total * 10 < int(listed) * 9:
        warned.append(
            f"the slices collected {_count(total)} tests, a tenth fewer than the "
            f"{_count(listed)} the table names, as when a module that failed an import "
            "skipped itself whole"
        )
    if unlisted.isdigit() and int(unlisted):
        due = int(unlisted) * 10 >= total
        warned.append(
            f"the table lacks {_count(unlisted)} of the {_count(total)} tests collected"
            + ("; a tenth or more, so it is due for a refresh (tests/README.md)" if due else "")
        )


def _summary(
    form: str,
    decide: Job,
    rows: Sequence[Row],
    wrong: Sequence[str],
    warned: Sequence[str],
) -> str:
    title = "the full run" if form == FULL else "the short check"
    out = [f"### `checks`: {title}, {'passed' if not wrong else 'did not pass'}", ""]
    if form == FULL and not decide.outputs.get("mode"):
        ended = decide.outputs.get("outcome") or decide.result
        out += [
            f"The step that decides the short check gave no answer (it ended in {_code(ended)}), "
            "so the run is full (ADR-067).",
            "",
        ]
    out += ["| Part | Its job ended | It took | It said |", "|---|---|---|---|"]
    out += [f"| {name} | {_code(ended)} | {took} | {said} |" for name, ended, took, said in rows]
    if wrong:
        out += ["", "It did not pass, because:", ""] + [f"- {line}" for line in wrong]
    if warned:
        out += ["", "Warnings:", ""] + [f"- {line}" for line in warned]
    if form == FULL and not wrong:
        out += ["", "The slices agree on what they cut, and together ran every test collected."]
    out += ["", "Each part names its own failures in its job's summary (ADR-078 point 8)."]
    return "\n".join(out) + "\n"


def _took(part: Job) -> str:
    seconds = part.outputs.get("seconds", "")
    return duration(int(seconds)) if seconds.isdigit() else ""


def duration(seconds: int) -> str:
    minutes, rest = divmod(seconds, 60)
    return f"{minutes} min {rest:02d} s" if minutes else f"{rest} s"


def _count(value: object) -> str:
    return f"{int(str(value)):,}" if str(value).isdigit() else _code(str(value))


def _code(text: str) -> str:
    """Text a tool or an author chose, set in a code span, so none of it renders as
    Markdown (ADR-067 point 9)."""
    return "`" + text.replace("`", "'").replace("\n", " ") + "`"


def _append(env: Mapping[str, str], name: str, text: str) -> None:
    if env.get(name):
        with open(env[name], "a", encoding="utf-8") as out:
            out.write(text)


# --- the command ------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(prog="ci_parts.py", description=DESCRIPTION)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run one part of the aggregator")
    which = run.add_mutually_exclusive_group(required=True)
    which.add_argument("--shard", metavar="i/N")
    which.add_argument("--rest", action="store_true")
    which.add_argument("--short", action="store_true")
    judge = commands.add_parser("verdict", help="the verdict of checks, in one form")
    judge.add_argument("form", choices=[FULL, SHORT])
    judge.add_argument("--slices", type=int, default=0)
    args = parser.parse_args(argv)

    if args.command == "run":
        if args.shard is not None:
            matched = re.fullmatch(r"([1-9][0-9]*)/([1-9][0-9]*)", args.shard)
            if matched is None or int(matched[1]) > int(matched[2]):
                parser.error(f"--shard is i/N, with 1 <= i <= N, not {args.shard!r}")
            part = ["--shard", args.shard]
        else:
            part = ["--rest"] if args.rest else ["--short"]
        return run_part(part, env)

    if args.form == FULL and args.slices < 1:
        parser.error("the full form needs the number of slices, --slices N")
    try:
        needs = json.loads(env.get("PKIT_NEEDS") or "{}")
    except ValueError:
        needs = {}
    needs = cast("Mapping[str, Any]", needs) if isinstance(needs, Mapping) else {}
    found = verdict(args.form, args.slices, needs, env.get("GITHUB_EVENT_NAME", ""))
    print(found.summary, end="")
    _append(env, "GITHUB_STEP_SUMMARY", found.summary)
    return 0 if found.passed else 1


if __name__ == "__main__":
    sys.exit(main())
