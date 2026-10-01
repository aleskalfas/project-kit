"""Tests for `pkit friction resolve` (Task #1181, COR-050 point 3).

Every test stands up a real adopter repository, commits a page on `main`,
revalidates it on a branch and again on `main`, and merges `main` into the
branch, so git itself leaves the conflict the command resolves: the three
versions it reads are git's index stages, and what it writes is checked
against the file and the index git hold afterwards.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime

import pytest
from click.testing import CliRunner, Result

from project_kit import friction_check as fc
from project_kit import friction_write as fw
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, friction_config, guide

PAGE = "docs/guide.md"
T0 = "2026-09-01T09:00:00Z"  # the common ancestor's revalidation
T1 = "2026-10-01T09:00:00Z"  # this branch's
T2 = "2026-10-02T09:40:12Z"  # the base side's, on `main`
LATER = datetime(2026, 10, 5, 10, 0, 0, tzinfo=UTC)

BODY = "The CLI takes one flag.\n"
UNCHANGED_COMMAND = (
    "pkit friction revalidate docs/guide.md --outcome unchanged "
    "--because '<why the content still holds>'"
)
UPDATED_COMMAND = "pkit friction revalidate docs/guide.md --outcome updated"


def _page(
    at: str,
    outcome: str = "unchanged",
    because: str | None = "the CLI is as described",
    *,
    body: str = BODY,
    deferred: str = "",
) -> str:
    """The page in block style, its own field after the block and a body beneath."""
    block = f"    revalidated:\n      at: {at}\n      outcome: {outcome}\n"
    if because is not None:
        block += f"      unchanged-because: {because}\n"
    return (
        "---\nid: guide\npkit:\n  friction:\n    anchors:\n      path: [src/cli/**]\n"
        f"{block}{deferred}status: draft\n---\n\n# The guide\n\n{body}"
    )


ANCESTOR = _page(T0, "updated", None)
THIS = _page(T1, because="this branch's refactor moves nothing the guide says")
BASE = _page(T2, because="the base's rename keeps every flag")


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    adopter = make_adopter_repo()
    adopter.git("config", "core.autocrlf", "false")
    return adopter


def _merge(
    repo: AdopterRepo,
    ancestor: Mapping[str, str],
    this: Mapping[str, str],
    base: Mapping[str, str],
) -> None:
    """Commit `ancestor` on `main`, `this` on branch `topic`, `base` on `main`, then merge
    `main` into `topic` — which leaves the conflict to resolve."""
    repo.write({CONFIG: friction_config(), **SOURCE, **ancestor})
    repo.commit("ancestor")
    repo.checkout("topic", create=True)
    repo.commit("this branch", dict(this))
    repo.checkout("main")
    repo.commit("the base side", dict(base))
    repo.checkout("topic")
    merged = repo.git("merge", "-q", "--no-edit", "main", check=False)
    assert merged.returncode == 1, merged.stdout + merged.stderr


def _cli(*args: str) -> Result:
    return CliRunner().invoke(main, ["friction", "resolve", *args])


def _read(repo: AdopterRepo, rel: str = PAGE) -> str:
    return (repo.root / rel).read_bytes().decode("utf-8")


def _unmerged(repo: AdopterRepo) -> set[str]:
    return set(repo.git("diff", "--name-only", "--diff-filter=U").stdout.split())


# --- resolved ------------------------------------------------------------------------


def test_a_conflict_only_in_the_block_takes_the_base_sides_and_stages_it(
    repo: AdopterRepo,
) -> None:
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})
    assert "<<<<<<<" in _read(repo)

    result = _cli()

    assert result.exit_code == 0, result.output
    assert _read(repo) == BASE
    assert _unmerged(repo) == set()
    assert repo.git("diff", "--cached", "--name-only").stdout.split() == [PAGE]
    assert f"{PAGE} — resolved and staged" in result.output
    assert f"{PAGE} now carries the base side's answer: at {T2}, unchanged" in result.output
    assert UNCHANGED_COMMAND in result.output
    assert "its content is the base side's" in result.output
    repo.git("commit", "-q", "--no-edit")  # nothing is left in conflict


def test_the_rest_of_the_file_is_gits_merge(repo: AdopterRepo) -> None:
    """A change of this branch's elsewhere — its own field, the body — is kept beside the
    base side's block; a change of the base side's elsewhere is kept too."""
    this = _page(T1, because="a reason", body=BODY + "\nA new section.\n").replace(
        "status: draft", "status: review"
    )
    base = _page(T2, because="the base's reason").replace("# The guide", "# The CLI guide")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: base})

    result = _cli()

    assert result.exit_code == 0, result.output
    expected = _page(T2, because="the base's reason", body=BODY + "\nA new section.\n")
    expected = expected.replace("status: draft", "status: review")
    assert _read(repo) == expected.replace("# The guide", "# The CLI guide")


def test_the_outcome_named_is_updated_only_when_the_content_differs_from_the_base_sides(
    repo: AdopterRepo,
) -> None:
    this = _page(T1, "updated", None, body="The CLI takes two flags.\n")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: BASE})

    result = _cli()

    assert result.exit_code == 0, result.output
    assert UPDATED_COMMAND + "\n" in result.output
    assert "--because" not in result.output.split(UPDATED_COMMAND, 1)[1].split("\n", 1)[0]
    assert "its content differs from the base side's" in result.output


def test_a_body_only_the_base_side_changed_is_unchanged_for_this_branch(
    repo: AdopterRepo,
) -> None:
    base = _page(T2, "updated", None, body="The CLI takes two flags.\n")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: base})

    result = _cli()

    assert result.exit_code == 0, result.output
    assert _read(repo) == base
    assert UNCHANGED_COMMAND in result.output


@pytest.mark.parametrize("outcome", ["updated", "unchanged"])
def test_the_named_answer_is_the_one_the_change_check_accepts(
    repo: AdopterRepo, outcome: str
) -> None:
    """Run as named once the merge is committed, the answer clears the friction this
    branch's change of an anchor raises — never a bump."""
    this = _page(T1, "updated", None, body="The CLI takes two flags.\n")
    if outcome == "unchanged":
        this = THIS
    _merge(
        repo,
        {PAGE: ANCESTOR},
        {PAGE: this, "src/cli/main.py": "print('cli, two flags')\n"},
        {PAGE: BASE},
    )
    result = _cli("--json")
    (owed,) = json.loads(result.output)["files"][0]["owed"]
    assert owed["outcome"] == outcome
    repo.git("commit", "-q", "--no-edit")

    before = fc.run_change_check(repo.root, "main")
    assert fc.FindingKind.FRICTION in {f.kind for f in before.findings if f.location == PAGE}
    because = "the second flag is described" if outcome == "unchanged" else None
    fw.write(fw.plan_revalidate(repo.root, PAGE, outcome=outcome, because=because, now=LATER))
    after = fc.run_change_check(repo.root, "main")
    kinds = {f.kind for f in after.findings if f.location == PAGE}
    assert kinds == {fc.FindingKind.ANSWERED}, after.findings


def test_crlf_line_endings_are_kept(repo: AdopterRepo) -> None:
    def crlf(text: str) -> str:
        return text.replace("\n", "\r\n")

    _merge(repo, {PAGE: crlf(ANCESTOR)}, {PAGE: crlf(THIS)}, {PAGE: crlf(BASE)})

    result = _cli()

    assert result.exit_code == 0, result.output
    assert _read(repo) == crlf(BASE)
    assert UNCHANGED_COMMAND in result.output


ONE_LINE = (
    "---\nid: guide\npkit: {{friction: {{anchors: {{path: [src/cli/**]}}, revalidated: "
    "{{at: {at}, outcome: unchanged, unchanged-because: {because}}}}}}}\n---\n\n{body}"
)


@pytest.mark.parametrize("layout", ["json", "one line"])
def test_front_matter_in_flow_style(repo: AdopterRepo, layout: str) -> None:
    def page(at: str, because: str) -> str:
        if layout == "json":
            return guide(at=at, because=because)
        return ONE_LINE.format(at=at, because=because, body=BODY)

    base = page(T2, "the base's reason")
    _merge(repo, {PAGE: page(T0, "first")}, {PAGE: page(T1, "this reason")}, {PAGE: base})

    result = _cli()

    assert result.exit_code == 0, result.output
    assert _read(repo) == base
    assert UNCHANGED_COMMAND in result.output


TERMS = "docs/terms.md"


def _terms(alpha: tuple[str, str], beta: tuple[str, str]) -> str:
    """A collection of two entries, each with its own block and its own section."""

    def entry(name: str, anchor: str, stamp: tuple[str, str]) -> str:
        return (
            f"{name}:\n  term: {name.title()}\n  pkit:\n    friction:\n"
            f"      anchors: {{path: [{anchor}]}}\n      revalidated:\n"
            f"        at: {stamp[0]}\n        outcome: unchanged\n"
            f"        unchanged-because: {stamp[1]}\n"
        )

    return (
        "---\n"
        + entry("alpha", "src/cli/**", alpha)
        + entry("beta", "src/core/**", beta)
        + "---\n\n## alpha\n\nAlpha text.\n\n## beta\n\nBeta text.\n"
    )


def test_each_entry_of_a_collection_takes_the_block_the_merge_gives_it(
    repo: AdopterRepo,
) -> None:
    """Both sides revalidated `alpha`: the base side's is taken, and it owes an answer.
    Only this branch revalidated `beta`: its block is kept, and nothing is owed."""
    first = (T0, "first")
    ancestor = _terms(first, first)
    this = _terms((T1, "this alpha"), (T1, "this beta"))
    base = _terms((T2, "base alpha"), first)
    _merge(repo, {TERMS: ancestor}, {TERMS: this}, {TERMS: base})

    result = _cli("--json")

    assert result.exit_code == 0, result.output
    assert _read(repo, TERMS) == _terms((T2, "base alpha"), (T1, "this beta"))
    (file,) = json.loads(result.output)["files"]
    assert [owed["location"] for owed in file["owed"]] == [f"{TERMS}#alpha"]


def test_a_deferral_only_this_branch_wrote_is_named(repo: AdopterRepo) -> None:
    deferral = (
        "      deferred:\n      - anchor: {kind: path, value: src/cli/**}\n"
        "        reason: the flag lands next week\n"
    )
    this = _page(T1, because="this reason", deferred=deferral)
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: BASE})

    human = _cli("--dry-run")
    assert "this branch's deferral of path:src/cli/** is not in the base side's block" in (
        human.output
    )
    assert (
        "pkit friction defer docs/guide.md --anchor 'path:src/cli/**' "
        "--reason '<why it can wait>'" in human.output
    )
    (owed,) = json.loads(_cli("--json").output)["files"][0]["owed"]
    assert owed["dropped_deferrals"] == [{"kind": "path", "value": "src/cli/**"}]
    assert _read(repo) == BASE


# --- left, skipped, nothing to do ----------------------------------------------------


def test_a_conflict_in_the_body_is_left_and_said(repo: AdopterRepo) -> None:
    this = _page(T0, "updated", None, body="The CLI takes two flags.\n")
    base = _page(T0, "updated", None, body="The CLI takes no flag.\n")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: base})
    conflicted = _read(repo)

    result = _cli()

    assert result.exit_code == 1, result.output
    assert f"{PAGE} — left as git left it: it conflicts in the body" in result.output
    assert "conflicts too" not in result.output
    assert _read(repo) == conflicted
    assert _unmerged(repo) == {PAGE}


def test_a_conflict_in_the_block_and_the_body_is_left_whole(repo: AdopterRepo) -> None:
    this = _page(T1, because="this reason", body="The CLI takes two flags.\n")
    base = _page(T2, because="the base's reason", body="The CLI takes no flag.\n")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: base})
    conflicted = _read(repo)

    result = _cli()

    assert result.exit_code == 1, result.output
    assert "it conflicts in the body" in result.output
    assert f"the `revalidated` block of {PAGE} conflicts too" in result.output
    assert _read(repo) == conflicted
    assert _unmerged(repo) == {PAGE}


def test_a_conflict_in_another_field_is_left(repo: AdopterRepo) -> None:
    this = THIS.replace("status: draft", "status: review")
    base = BASE.replace("status: draft", "status: final")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: base})

    result = _cli()

    assert result.exit_code == 1, result.output
    assert "it conflicts in the front matter, outside the `revalidated` blocks" in result.output
    assert _unmerged(repo) == {PAGE}


def test_a_file_that_is_not_an_artefacts_is_skipped(repo: AdopterRepo) -> None:
    _merge(
        repo,
        {PAGE: ANCESTOR},
        {PAGE: THIS, "src/cli/main.py": "print('this')\n"},
        {PAGE: BASE, "src/cli/main.py": "print('base')\n"},
    )
    named = _cli("docs/other.md", "--dry-run")
    assert "docs/other.md — skipped: not in conflict" in named.output

    result = _cli()

    assert result.exit_code == 0, result.output
    assert "src/cli/main.py — skipped: no declared place holds it" in result.output
    assert _unmerged(repo) == {"src/cli/main.py"}
    assert _read(repo) == BASE


def test_a_file_resolved_by_hand_is_left_alone(repo: AdopterRepo) -> None:
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})
    by_hand = _page("2026-10-03T08:00:00Z", because="both changes read together")
    repo.write({PAGE: by_hand})

    result = _cli(PAGE)

    assert result.exit_code == 0, result.output
    assert "holds no conflict marker any more" in result.output
    assert _read(repo) == by_hand


def test_dry_run_shows_the_resolution_and_writes_nothing(repo: AdopterRepo) -> None:
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})
    conflicted = _read(repo)

    result = _cli("--dry-run")

    assert result.exit_code == 0, result.output
    assert f"{PAGE} — would be resolved and staged" in result.output
    assert f"    -      at: {T1}\n" in result.output  # this branch's block goes
    assert "    -<<<<<<< HEAD\n" in result.output
    assert f"      at: {T2}\n" in result.output  # the base side's stays
    assert UNCHANGED_COMMAND in result.output
    assert "Dry run: nothing written." in result.output
    assert _read(repo) == conflicted
    assert _unmerged(repo) == {PAGE}
    document = json.loads(_cli("--dry-run", "--json").output)
    assert document["dry_run"] is True and document["files"][0]["staged"] is False


def test_outside_a_merge_there_is_nothing_to_resolve(repo: AdopterRepo) -> None:
    repo.write({CONFIG: friction_config(), **SOURCE, PAGE: ANCESTOR})
    repo.commit("ancestor")

    result = _cli()

    assert result.exit_code == 0, result.output
    assert "no merge is in progress: nothing to resolve" in result.output
    document = json.loads(_cli("--json").output)
    assert document["merging"] is False and document["files"] == []


def test_a_merge_without_a_conflict_has_nothing_to_resolve(repo: AdopterRepo) -> None:
    repo.write({CONFIG: friction_config(), **SOURCE, PAGE: ANCESTOR})
    repo.commit("ancestor")
    repo.checkout("topic", create=True)
    repo.commit("this branch", {PAGE: THIS})
    repo.checkout("main")
    repo.commit("the base side", {"src/core/engine.py": "ENGINE = 2\n"})
    repo.checkout("topic")
    repo.git("merge", "-q", "--no-commit", "--no-ff", "main")

    result = _cli()

    assert result.exit_code == 0, result.output
    assert "no file is in conflict: nothing to resolve" in result.output


def test_the_json_document(repo: AdopterRepo) -> None:
    _merge(
        repo,
        {PAGE: ANCESTOR},
        {PAGE: THIS, "src/cli/main.py": "print('this')\n"},
        {PAGE: BASE, "src/cli/main.py": "print('base')\n"},
    )

    result = _cli("--json")

    document = json.loads(result.output)
    assert document["schema_version"] == 1 and document["report"] == "resolve"
    assert document["merging"] is True and document["dry_run"] is False
    assert document["merge_head"] == repo.git("rev-parse", "main").stdout.strip()
    files = {f["path"]: f for f in document["files"]}
    assert files["src/cli/main.py"]["status"] == "skipped"
    page = files[PAGE]
    assert (page["status"], page["staged"], page["reason"]) == ("resolved", True, None)
    (owed,) = page["owed"]
    assert owed["artefact"] == "guide" and owed["location"] == PAGE
    assert owed["base_answer"] == {
        "at": T2,
        "outcome": "unchanged",
        "unchanged-because": "the base's rename keeps every flag",
    }
    assert owed["outcome"] == "unchanged" and owed["command"] == UNCHANGED_COMMAND
    assert owed["dropped_deferrals"] == []
