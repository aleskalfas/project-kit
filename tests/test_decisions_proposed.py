"""Tests for what a proposed record waits on (`waits-on`), its check, and the report of
the proposed records due for a person, `pkit decisions proposed` (#2166)."""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import decisions_proposed, github_issues
from project_kit.cli import main
from project_kit.decisions_proposed import Condition
from project_kit.github_issues import IssueReading
from project_kit.validators import Severity
from tests.adopter_repo import MakeAdopterRepo

TODAY = dt.date(2026, 10, 26)


def _record(
    path: Path,
    record_id: str,
    *,
    status: str = "proposed",
    date: str = "2026-10-20",
    waits_on: str = "",
) -> None:
    """A minimal decision record at `path`, its `waits-on` written as given."""
    path.parent.mkdir(parents=True, exist_ok=True)
    extra = f"waits-on: {waits_on}\n" if waits_on else ""
    path.write_text(
        f"---\nid: {record_id}\ntitle: x\nstatus: {status}\ndate: {date}\nauthor: t\n{extra}"
        "---\n\n## Context\n",
        encoding="utf-8",
    )


def _text(*, status: str = "proposed", waits_on: str = "") -> str:
    extra = f"waits-on: {waits_on}\n" if waits_on else ""
    return f"---\nid: PRJ-001\ntitle: x\nstatus: {status}\ndate: 2026-10-01\n{extra}---\n\nBody.\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project tree with the fixed decision namespaces present."""
    (tmp_path / ".pkit" / "decisions" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "decisions" / "project").mkdir(parents=True)
    return tmp_path


def _prj(project: Path, number: int) -> Path:
    return project / ".pkit" / "decisions" / "project" / f"PRJ-{number:03d}-x.md"


class _Issues:
    """An issue reader that answers from a table and counts what it is asked."""

    def __init__(self, states: dict[str, IssueReading]) -> None:
        self.states = states
        self.asked: list[str] = []

    def __call__(self, _root: Path, issue: str) -> IssueReading:
        self.asked.append(issue)
        return self.states[issue]


def _no_issues(_root: Path, issue: str) -> IssueReading:
    raise AssertionError(f"the report read issue {issue} it had no need of")


def _standings(found: decisions_proposed.ProposedReport) -> list[tuple[str, str]]:
    return [(record.record_id, record.standing) for record in found.records]


# --- the field's shape -------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "condition"),
    [
        ({"issue": 795}, Condition("issue", "795")),
        ({"issue": "aleskalfas/project-kit#795"}, Condition("issue", "aleskalfas/project-kit#795")),
        ({"date": "2026-12-01"}, Condition("date", "2026-12-01")),
        ({"record": "ADR-071"}, Condition("record", "ADR-071")),
        ({"record": "ADR-071-living-specification"}, Condition("record", "ADR-071")),
        ({"record": "COR-019"}, Condition("record", "COR-019")),
        ({"record": "PRJ-002"}, Condition("record", "PRJ-002")),
        (
            {"record": "project-management:DEC-059"},
            Condition("record", "project-management:DEC-059"),
        ),
        (
            {"record": "project-management:DEC-059-topology-of-seats"},
            Condition("record", "project-management:DEC-059"),
        ),
    ],
)
def test_a_condition_of_each_kind_is_read(value: dict[str, Any], condition: Condition) -> None:
    assert decisions_proposed.read_condition(value) == (condition, "")


@pytest.mark.parametrize(
    ("value", "says"),
    [
        ("#795", "is not a mapping"),
        (795, "is not a mapping"),
        ([{"issue": 795}], "is not a mapping"),
        (None, "is not a mapping"),
        ({}, "names no condition"),
        ({"issue": 795, "date": "2026-12-01"}, "names 2 conditions"),
        ({"until": "2026-12-01"}, "`until`, no kind of condition"),
        ({"issue": None}, "since `#` opens a comment in YAML"),
        ({"issue": 0}, "names no issue"),
        ({"issue": -3}, "names no issue"),
        ({"issue": True}, "names no issue"),
        ({"issue": "795"}, "names no issue"),
        ({"issue": "#795"}, "names no issue"),
        ({"issue": "-x/y#795"}, "names no issue"),
        ({"date": "2026-02-30"}, "is no date"),
        ({"date": "1 December 2026"}, "is no date"),
        ({"date": 20261201}, "is no date"),
        ({"record": "DEC-059"}, "names no record"),
        ({"record": "project-management:ADR-071"}, "names no record"),
        ({"record": "[project-management:DEC-059]"}, "names no record"),
        ({"record": ["project-management:DEC-059"]}, "names no record"),
        ({"record": "ADR-071#4"}, "names no record"),
        ({"record": "RS-WRITE-007"}, "names no record"),
    ],
)
def test_a_value_that_names_no_condition_says_why(value: Any, says: str) -> None:
    condition, why = decisions_proposed.read_condition(value)
    assert condition is None
    assert says in why


def test_a_proposed_record_that_waits_on_one_condition_passes() -> None:
    assert decisions_proposed.check_waits_on("r.md", _text(waits_on="{issue: 795}")) == []


def test_a_record_without_the_field_passes_whatever_its_status() -> None:
    for status in ("proposed", "accepted", "superseded"):
        assert decisions_proposed.check_waits_on("r.md", _text(status=status)) == []


def test_a_field_that_names_no_condition_fails_at_its_pointer() -> None:
    [finding] = decisions_proposed.check_waits_on("r.md", _text(waits_on="{issue: 795, date: x}"))
    assert finding.location == "r.md:/waits-on"
    assert finding.severity is Severity.ERROR
    assert "names 2 conditions" in finding.message


def test_an_issue_written_with_its_hash_fails_and_says_why() -> None:
    """`#795` opens a YAML comment, so the field reads as empty."""
    text = _text(waits_on="\n  issue: #795")
    [finding] = decisions_proposed.check_waits_on("r.md", text)
    assert finding.severity is Severity.ERROR
    assert "Write the number alone, `issue: 795`" in finding.message


def test_a_field_on_a_record_that_is_not_proposed_warns() -> None:
    [finding] = decisions_proposed.check_waits_on(
        "r.md", _text(status="accepted", waits_on="{issue: 795}")
    )
    assert finding.location == "r.md:/waits-on"
    assert finding.severity is Severity.WARNING
    assert "`accepted`" in finding.message


def test_a_malformed_field_on_an_accepted_record_fails_and_warns() -> None:
    found = decisions_proposed.check_waits_on("r.md", _text(status="accepted", waits_on="soon"))
    assert [finding.severity for finding in found] == [Severity.ERROR, Severity.WARNING]


def test_front_matter_that_does_not_parse_fails_once_when_it_writes_the_field() -> None:
    text = "---\nid: PRJ-001\nstatus: proposed\nwaits-on: {issue: 795\n---\n\nBody.\n"
    [finding] = decisions_proposed.check_waits_on("r.md", text)
    assert finding.severity is Severity.ERROR
    assert "the front matter does not parse" in finding.message


def test_front_matter_that_does_not_parse_without_the_field_raises_nothing() -> None:
    text = "---\nid: PRJ-001\nstatus: proposed\ntitle: [x\n---\n\nBody.\n"
    assert decisions_proposed.check_waits_on("r.md", text) == []


# --- the report: a condition that has passed -----------------------------------------


@pytest.mark.parametrize(
    ("state", "standing", "says"),
    [
        ("closed", "due", "waits on issue #795, which is closed."),
        ("open", "waiting", "waits on issue #795, which is open."),
    ],
)
def test_an_issue_condition_is_due_once_the_issue_closes(
    project: Path, state: str, standing: str, says: str
) -> None:
    _record(_prj(project, 1), "PRJ-001", waits_on="{issue: 795}")
    issues = _Issues({"795": IssueReading(state)})

    found = decisions_proposed.report(project, today=TODAY, read=issues)

    [record] = found.records
    assert (record.record_id, record.standing, record.reason) == ("PRJ-001", standing, says)
    assert record.path == ".pkit/decisions/project/PRJ-001-x.md"


def test_an_issue_that_could_not_be_read_says_why(project: Path) -> None:
    _record(_prj(project, 1), "PRJ-001", waits_on="{issue: owner/repo#12}")
    issues = _Issues({"owner/repo#12": IssueReading("unknown", "`gh` exited 1: no network")})

    [record] = decisions_proposed.report(project, today=TODAY, read=issues).records

    assert record.standing == "unread"
    assert record.reason == (
        "waits on issue owner/repo#12, which could not be read: `gh` exited 1: no network."
    )


def test_each_issue_is_read_once(project: Path) -> None:
    _record(_prj(project, 1), "PRJ-001", waits_on="{issue: 795}")
    _record(_prj(project, 2), "PRJ-002", waits_on="{issue: 795}")
    issues = _Issues({"795": IssueReading("open")})

    decisions_proposed.report(project, today=TODAY, read=issues)

    assert issues.asked == ["795"]


@pytest.mark.parametrize(
    ("date", "standing", "says"),
    [
        ("2026-10-25", "due", "waits on the date 2026-10-25, which has come."),
        ("2026-10-26", "due", "waits on the date 2026-10-26, which has come."),
        ("2026-10-27", "waiting", "waits on the date 2026-10-27, 1 day(s) ahead."),
    ],
)
def test_a_date_condition_is_due_once_the_date_comes(
    project: Path, date: str, standing: str, says: str
) -> None:
    _record(_prj(project, 1), "PRJ-001", waits_on=f"{{date: {date}}}")

    [record] = decisions_proposed.report(project, today=TODAY, read=_no_issues).records

    assert (record.standing, record.reason) == (standing, says)


@pytest.mark.parametrize(
    ("status", "standing", "says"),
    [
        ("accepted", "due", "waits on record PRJ-009, which is accepted."),
        ("superseded", "due", "waits on record PRJ-009, which is superseded."),
        ("proposed", "waiting", "waits on record PRJ-009, which is still proposed."),
    ],
)
def test_a_record_condition_is_due_once_the_record_is_accepted(
    project: Path, status: str, standing: str, says: str
) -> None:
    _record(_prj(project, 1), "PRJ-001", waits_on="{record: PRJ-009}")
    _record(_prj(project, 9), "PRJ-009", status=status)

    found = decisions_proposed.report(project, today=TODAY, read=_no_issues)

    [record] = [record for record in found.records if record.record_id == "PRJ-001"]
    assert (record.standing, record.reason) == (standing, says)


def test_a_record_condition_that_names_no_record_here_is_due(project: Path) -> None:
    _record(_prj(project, 1), "PRJ-001", waits_on="{record: ADR-099}")

    [record] = decisions_proposed.report(project, today=TODAY, read=_no_issues).records

    assert (record.standing, record.reason) == (
        "due",
        "waits on record ADR-099, which no record here holds.",
    )


def test_a_capabilitys_decision_is_read_by_its_capability(project: Path) -> None:
    decisions = project / ".pkit" / "capabilities" / "alpha" / "decisions"
    _record(decisions / "DEC-001-a.md", "DEC-001", status="accepted")
    _record(decisions / "DEC-002-b.md", "DEC-002", waits_on="{record: 'alpha:DEC-001'}")
    _record(_prj(project, 1), "PRJ-001", waits_on="{record: beta:DEC-001}")

    found = decisions_proposed.report(project, today=TODAY, read=_no_issues)

    assert [(r.record_id, r.standing, r.reason) for r in found.records] == [
        ("alpha:DEC-002", "due", "waits on record alpha:DEC-001, which is accepted."),
        ("PRJ-001", "due", "waits on record beta:DEC-001, which no record here holds."),
    ]


def test_a_field_that_names_no_condition_could_not_be_read(project: Path) -> None:
    _record(_prj(project, 1), "PRJ-001", waits_on="soon")

    [record] = decisions_proposed.report(project, today=TODAY, read=_no_issues).records

    assert record.standing == "unread"
    assert record.reason.startswith("its `waits-on` is not a mapping")


def test_front_matter_that_does_not_parse_could_not_be_read(project: Path) -> None:
    path = _prj(project, 1)
    path.write_text("---\nid: PRJ-001\nstatus: proposed\ntitle: [x\n---\n\nBody.\n")

    [record] = decisions_proposed.report(project, today=TODAY, read=_no_issues).records

    assert record.standing == "unread"
    assert record.reason.startswith("its front matter does not parse")


# --- the report: a record that names no condition ----------------------------------


@pytest.mark.parametrize(
    ("date", "standing", "says"),
    [
        (
            "2026-09-25",
            "due",
            "names no condition, and has been proposed since 2026-09-25, 31 day(s), more "
            "than the 30 the report allows.",
        ),
        (
            "2026-09-26",
            "waiting",
            "names no condition, and has been proposed since 2026-09-26, 30 day(s).",
        ),
    ],
)
def test_a_record_with_no_condition_is_due_past_the_threshold(
    project: Path, date: str, standing: str, says: str
) -> None:
    _record(_prj(project, 1), "PRJ-001", date=date)

    [record] = decisions_proposed.report(project, today=TODAY, read=_no_issues).records

    assert (record.standing, record.reason, record.since) == (standing, says, date)


def test_the_threshold_is_the_callers(project: Path) -> None:
    _record(_prj(project, 1), "PRJ-001", date="2026-10-20")

    found = decisions_proposed.report(project, today=TODAY, read=_no_issues, older_than=5)

    assert _standings(found) == [("PRJ-001", "due")]
    assert found.older_than == 5


def test_a_record_with_no_condition_and_no_date_it_can_read_could_not_be_read(
    project: Path,
) -> None:
    _record(_prj(project, 1), "PRJ-001", date="soon")

    [record] = decisions_proposed.report(project, today=TODAY, read=_no_issues).records

    assert record.standing == "unread"
    assert record.since is None
    assert "its `date` cannot be read" in record.reason


# --- the report: which records ------------------------------------------------------


def test_only_proposed_records_are_listed_in_every_id_space(project: Path) -> None:
    overlay = project / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text("adr-records:\n  - docs/adr/\n", encoding="utf-8")
    _record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001")
    _record(_prj(project, 1), "PRJ-001", status="accepted")
    _record(project / "docs" / "adr" / "ADR-001-a.md", "ADR-001")
    capability = project / ".pkit" / "capabilities" / "alpha" / "decisions"
    _record(capability / "DEC-001-a.md", "DEC-001", status="superseded")

    found = decisions_proposed.report(project, today=TODAY, read=_no_issues)

    assert sorted(record.record_id for record in found.records) == ["ADR-001", "COR-001"]


def test_the_report_orders_due_then_unread_then_waiting_oldest_first(project: Path) -> None:
    _record(_prj(project, 1), "PRJ-001", date="2026-10-01", waits_on="{date: 2027-01-01}")
    _record(_prj(project, 2), "PRJ-002", date="2026-09-01", waits_on="{issue: 1}")
    _record(_prj(project, 3), "PRJ-003", date="2026-08-01")
    _record(_prj(project, 4), "PRJ-004", date="2026-07-01", waits_on="{date: 2026-08-01}")
    _record(_prj(project, 5), "PRJ-005", date="2026-06-01", waits_on="{record: PRJ-003}")
    issues = _Issues({"1": IssueReading("unknown", "offline")})

    found = decisions_proposed.report(project, today=TODAY, read=issues)

    assert _standings(found) == [
        ("PRJ-004", "due"),
        ("PRJ-003", "due"),
        ("PRJ-002", "unread"),
        ("PRJ-005", "waiting"),
        ("PRJ-001", "waiting"),
    ]


def test_a_synced_copy_is_not_listed_and_a_record_may_wait_on_one(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The project does not settle a record it receives by sync, which is settled where
    it is authored (COR-055 point 1)."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    decisions = repo.root / ".pkit" / "decisions"
    _record(decisions / "core" / "COR-900-a.md", "COR-900", date="2026-01-01")
    _record(decisions / "core" / "COR-901-a.md", "COR-901", status="accepted")
    capability = repo.root / ".pkit" / "capabilities" / "living-docs" / "decisions"
    _record(capability / "DEC-900-a.md", "DEC-900", date="2026-01-01")
    _record(decisions / "project" / "PRJ-900-a.md", "PRJ-900", waits_on="{record: COR-901}")

    found = decisions_proposed.report(repo.root, today=TODAY, read=_no_issues)

    assert [(r.record_id, r.standing) for r in found.records] == [("PRJ-900", "due")]


# --- reading an issue -----------------------------------------------------------------


def test_an_issue_is_read_by_the_backbones_reader_from_the_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, 0, '{"state": "CLOSED"}', "")

    monkeypatch.setattr(github_issues.subprocess, "run", run)

    assert decisions_proposed.read_issue(tmp_path, "795") == IssueReading("closed")
    [call] = calls
    assert call["args"][:4] == ["gh", "issue", "view", "795"]
    assert call["cwd"] == tmp_path


def test_an_issue_the_reader_cannot_read_is_unread_with_its_reason(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(*_args: Any, **_kwargs: Any) -> None:
        raise FileNotFoundError("gh")

    monkeypatch.setattr(github_issues.subprocess, "run", run)
    _record(_prj(project, 1), "PRJ-001", waits_on="{issue: 795}")

    [record] = decisions_proposed.report(project, today=TODAY).records

    assert record.standing == "unread"
    assert record.reason == (
        "waits on issue #795, which could not be read: `gh`, the GitHub client, is not installed."
    )


# --- the command -----------------------------------------------------------------------


def _in_git(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    monkeypatch.chdir(project)


def test_cli_lists_each_standing_and_exits_zero(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _in_git(project, monkeypatch)
    _record(_prj(project, 1), "PRJ-001", date="2026-01-01")
    _record(_prj(project, 2), "PRJ-002", waits_on="{issue: 795}")
    _record(_prj(project, 3), "PRJ-003", waits_on="{date: 2999-01-01}")
    monkeypatch.setattr(
        decisions_proposed, "read_issue", lambda _root, _issue: IssueReading("unknown", "offline")
    )

    result = CliRunner().invoke(main, ["decisions", "proposed"])

    assert result.exit_code == 0, result.output
    assert "3 proposed record(s) of the project's own: 1 due, 1 unread, 1 waiting." in (
        result.output
    )
    assert "Due for a person to settle (1):" in result.output
    assert "PRJ-001  .pkit/decisions/project/PRJ-001-x.md" in result.output
    assert "Could not be read (1):" in result.output
    assert "waits on issue #795, which could not be read: offline." in result.output
    assert "Waiting (1):" in result.output
    assert result.output.index("Due for") < result.output.index("Could not be read")
    assert result.output.index("Could not be read") < result.output.index("Waiting (1)")


def test_cli_takes_the_threshold(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _in_git(project, monkeypatch)
    _record(_prj(project, 1), "PRJ-001", date=(dt.date.today() - dt.timedelta(days=3)).isoformat())

    result = CliRunner().invoke(main, ["decisions", "proposed", "--older-than", "2"])

    assert result.exit_code == 0, result.output
    assert "more than the 2 the report allows." in result.output


def test_cli_with_no_proposed_record_says_so(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _in_git(project, monkeypatch)
    _record(_prj(project, 1), "PRJ-001", status="accepted")

    result = CliRunner().invoke(main, ["decisions", "proposed"])

    assert result.exit_code == 0, result.output
    assert "No proposed record of the project's own." in result.output


def test_cli_threshold_defaults_to_the_reports() -> None:
    from project_kit.cli import decisions_proposed as command

    [option] = [param for param in command.params if param.name == "older_than"]
    assert option.default == decisions_proposed.DEFAULT_OLDER_THAN


def test_cli_refuses_a_negative_threshold(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _in_git(project, monkeypatch)
    result = CliRunner().invoke(main, ["decisions", "proposed", "--older-than", "-1"])
    assert result.exit_code == 2
