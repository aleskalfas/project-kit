"""Tests for `pkit friction resolve` (Task #1181, COR-050 points 3 and 4).

Every test stands up a real adopter repository, commits a page on `main`,
changes it on a branch and again on `main`, and merges `main` into the
branch, so git itself leaves the conflict the command resolves: the three
versions it reads are git's index stages, and what it writes is checked
against the file and the index git hold afterwards.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest
from click.testing import CliRunner, Result
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import default_branch as db
from project_kit import friction_check as fc
from project_kit import friction_resolve as fres
from project_kit import friction_write as fw
from project_kit.cli import main
from project_kit.friction_discovery import split_front_matter
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
BOTH_ANCHORS = "[src/cli/**, src/core/**]"

_safe = YAML(typ="safe")


def _deferral(value: str, reason: str) -> str:
    return f"      - anchor: {{kind: path, value: {value}}}\n        reason: {reason}\n"


def _deferred(*entries: tuple[str, str]) -> str:
    """A page's `deferred` list, written as a person writes it."""
    return "      deferred:\n" + "".join(_deferral(v, r) for v, r in entries)


def _page(
    at: str,
    outcome: str = "unchanged",
    because: str | None = "the CLI is as described",
    *,
    body: str = BODY,
    deferred: str = "",
    anchors: str = "[src/cli/**]",
) -> str:
    """The page in block style, its own field after the block and a body beneath."""
    block = f"    revalidated:\n      at: {at}\n      outcome: {outcome}\n"
    if because is not None:
        block += f"      unchanged-because: {because}\n"
    return (
        f"---\nid: guide\npkit:\n  friction:\n    anchors:\n      path: {anchors}\n"
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


@pytest.fixture(autouse=True)
def no_check_base_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's own `$PKIT_CHECK_BASE` must not decide which base these merges have."""
    monkeypatch.delenv(db.CHECK_BASE_ENV, raising=False)


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


def _cli(*args: str, input: str | None = None) -> Result:
    return CliRunner().invoke(main, ["friction", "resolve", *args], input=input)


def _read(repo: AdopterRepo, rel: str = PAGE) -> str:
    return (repo.root / rel).read_bytes().decode("utf-8")


def _unmerged(repo: AdopterRepo) -> set[str]:
    return set(repo.git("diff", "--name-only", "--diff-filter=U").stdout.split())


def _revalidated(repo: AdopterRepo, *keys: str) -> Any:
    """The `revalidated` block the page — or a collection entry, by `keys` — now holds."""
    front_matter, _body = split_front_matter(_read(repo, TERMS if keys else PAGE))
    holder: Any = bs.as_written(_safe.load(front_matter or ""))
    for key in keys:
        holder = holder[key]
    return holder["pkit"]["friction"]["revalidated"]


# --- resolved ------------------------------------------------------------------------


def test_a_conflict_only_in_the_block_takes_the_base_sides_and_writes_it_unstaged(
    repo: AdopterRepo,
) -> None:
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})
    assert "<<<<<<<" in _read(repo)

    result = _cli()

    assert result.exit_code == 0, result.output
    assert _read(repo) == BASE
    assert _unmerged(repo) == {PAGE}  # written, not staged: no consent was given
    assert f"{PAGE} — resolved and written" in result.output
    assert f"{PAGE} now carries the base side's answer: at {T2}, unchanged" in result.output
    assert UNCHANGED_COMMAND in result.output
    assert "its content is the base side's" in result.output
    assert "Not staged." in result.output
    assert f"  git add -- {PAGE}\n" in result.output
    assert "git checkout -m -- <path>" in result.output


def test_yes_stages_the_resolved_file(repo: AdopterRepo) -> None:
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})

    result = _cli("--yes")

    assert result.exit_code == 0, result.output
    assert _unmerged(repo) == set()
    assert repo.git("diff", "--cached", "--name-only").stdout.split() == [PAGE]
    assert f"Staged {PAGE}" in result.output
    repo.git("commit", "-q", "--no-edit")  # nothing is left in conflict


@pytest.mark.parametrize(("answer", "staged"), [("y", True), ("n", False)])
def test_a_terminal_is_asked_after_the_diff_before_staging(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch, answer: str, staged: bool
) -> None:
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})
    monkeypatch.setattr(fw, "interactive", lambda: True)

    result = _cli(input=f"{answer}\n")

    assert result.exit_code == 0, result.output
    assert result.output.index(f"+++ b/{PAGE}") < result.output.index("Stage the resolved files")
    assert _read(repo) == BASE
    assert _unmerged(repo) == (set() if staged else {PAGE})
    assert (f"  git add -- {PAGE}\n" in result.output) is not staged


def test_the_conflict_comes_back_with_checkout_merge(repo: AdopterRepo) -> None:
    """The undo the command prints: `git checkout -m` restores git's conflict, staged or not."""
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})
    assert _cli("--yes").exit_code == 0

    repo.git("checkout", "-m", "--", PAGE)

    assert _unmerged(repo) == {PAGE}
    assert "<<<<<<<" in _read(repo)
    assert _cli().exit_code == 0  # git's conflict again, so it resolves again
    assert _read(repo) == BASE


def test_the_rest_of_the_file_is_gits_merge(repo: AdopterRepo) -> None:
    """A change of this branch's elsewhere — its own field, the body — is kept beside the
    base side's block; a change of the base side's elsewhere is kept too."""

    def titled(page: str, title: str = "Guide") -> str:
        return page.replace("---\nid: guide\n", f"---\ntitle: {title}\nid: guide\n", 1)

    this = titled(_page(T1, because="a reason", body=BODY + "\nA new section.\n"), "The guide")
    base = titled(_page(T2, because="the base's reason")).replace("# The guide", "# The CLI guide")
    _merge(repo, {PAGE: titled(ANCESTOR)}, {PAGE: this}, {PAGE: base})

    result = _cli()

    assert result.exit_code == 0, result.output
    expected = titled(_page(T2, because="the base's reason", body=BODY + "\nA new section.\n"))
    expected = expected.replace("title: Guide", "title: The guide")
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
    result = _cli("--json", "--yes")
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


def _crlf(text: str) -> str:
    return text.replace("\n", "\r\n")


def test_crlf_line_endings_are_kept(repo: AdopterRepo) -> None:
    _merge(repo, {PAGE: _crlf(ANCESTOR)}, {PAGE: _crlf(THIS)}, {PAGE: _crlf(BASE)})

    result = _cli()

    assert result.exit_code == 0, result.output
    assert _read(repo) == _crlf(BASE)
    assert UNCHANGED_COMMAND in result.output


def test_a_crlf_checkout_of_lf_text_is_written_back_in_crlf(repo: AdopterRepo) -> None:
    """With `text eol=crlf` the index holds `\\n` and the working tree `\\r\\n`: the file is
    written as checked out, and staged it is normalised again."""
    _merge(
        repo,
        {".gitattributes": "*.md text eol=crlf\n", PAGE: ANCESTOR},
        {PAGE: THIS},
        {PAGE: BASE},
    )
    assert "\r\n" in _read(repo)

    result = _cli("--yes")

    assert result.exit_code == 0, result.output
    assert _read(repo) == _crlf(BASE)
    assert repo.git("cat-file", "blob", f":{PAGE}").stdout == BASE


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


def _entry(
    name: str,
    anchors: str,
    stamp: tuple[str, str],
    deferred: tuple[tuple[str, str], ...] = (),
) -> str:
    """One entry of a collection, its block in block style."""
    lines = (
        f"{name}:\n  term: {name.title()}\n  pkit:\n    friction:\n"
        f"      anchors: {{path: {anchors}}}\n      revalidated:\n"
        f"        at: {stamp[0]}\n        outcome: unchanged\n"
        f"        unchanged-because: {stamp[1]}\n"
    )
    if deferred:
        lines += "        deferred:\n" + "".join(
            f"        - anchor: {{kind: path, value: {v}}}\n          reason: {r}\n"
            for v, r in deferred
        )
    return lines


def _collection(*entries: str) -> str:
    return "---\n" + "".join(entries) + "---\n\n## alpha\n\nAlpha text.\n\n## beta\n\nBeta text.\n"


def _terms(alpha: tuple[str, str], beta: tuple[str, str]) -> str:
    """A collection of two entries, each with its own block and its own section."""
    return _collection(
        _entry("alpha", "[src/cli/**]", alpha), _entry("beta", "[src/core/**]", beta)
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


def test_a_sibling_entry_git_merged_cleanly_keeps_gits_merge(repo: AdopterRepo) -> None:
    """Only the entries whose blocks git conflicted on are decided. `main` re-answered
    `beta` and this branch deferred one more of its anchors a few lines below: git merged
    that, and it stays merged — the deferral kept, nothing owed for `beta`."""
    first = (T0, "first")
    cli_deferral = ("src/cli/**", "the cli lands later")
    core_deferral = ("src/core/**", "the core lands later")
    ancestor = _collection(
        _entry("alpha", "[src/cli/**]", first),
        _entry("beta", BOTH_ANCHORS, first, (cli_deferral,)),
    )
    this = _collection(
        _entry("alpha", "[src/cli/**]", (T1, "this alpha")),
        _entry("beta", BOTH_ANCHORS, first, (cli_deferral, core_deferral)),
    )
    base = _collection(
        _entry("alpha", "[src/cli/**]", (T2, "base alpha")),
        _entry("beta", BOTH_ANCHORS, (T2, "base beta"), (cli_deferral,)),
    )
    _merge(repo, {TERMS: ancestor}, {TERMS: this}, {TERMS: base})

    result = _cli("--json")

    assert result.exit_code == 0, result.output
    assert _read(repo, TERMS) == _collection(
        _entry("alpha", "[src/cli/**]", (T2, "base alpha")),
        _entry("beta", BOTH_ANCHORS, (T2, "base beta"), (cli_deferral, core_deferral)),
    )
    (file,) = json.loads(result.output)["files"]
    assert [owed["location"] for owed in file["owed"]] == [f"{TERMS}#alpha"]


def test_a_deferral_this_branch_wrote_is_kept_beside_the_base_sides_answer(
    repo: AdopterRepo,
) -> None:
    """Both sides revalidated; this branch also deferred an anchor. The base side's answer
    is taken and the deferral kept (COR-050 point 4): it is not dropped."""
    this = _page(T1, because="this reason", deferred=_deferred(("src/cli/**", "next week")))
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: BASE})

    result = _cli("--json")

    assert result.exit_code == 0, result.output
    assert _revalidated(repo) == {
        "at": T2,
        "outcome": "unchanged",
        "unchanged-because": "the base's rename keeps every flag",
        "deferred": [{"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "next week"}],
    }
    (owed,) = json.loads(result.output)["files"][0]["owed"]
    assert "dropped_deferrals" not in owed
    assert owed["base_answer"] == {
        "at": T2,
        "outcome": "unchanged",
        "unchanged-because": "the base's rename keeps every flag",
    }


def test_a_deferral_on_one_side_and_a_revalidation_on_the_other_owe_nothing(
    repo: AdopterRepo,
) -> None:
    """Only one side revalidated: its answer is taken, the other side's deferral is kept,
    and no revalidation is owed — this is no two revalidations conflicting."""
    ancestor = _page(T0, because="first")
    this = _page(T0, because="first", deferred=_deferred(("src/cli/**", "next week")))
    _merge(repo, {PAGE: ancestor}, {PAGE: this}, {PAGE: BASE})

    result = _cli("--json")

    assert result.exit_code == 0, result.output
    assert _revalidated(repo) == {
        "at": T2,
        "outcome": "unchanged",
        "unchanged-because": "the base's rename keeps every flag",
        "deferred": [{"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "next week"}],
    }
    assert json.loads(result.output)["files"][0]["owed"] == []
    assert _read(repo).endswith("status: draft\n---\n\n# The guide\n\n" + BODY)


@pytest.mark.parametrize("layout", ["block", "json"])
def test_parallel_deferrals_of_different_anchors_merge(repo: AdopterRepo, layout: str) -> None:
    def page(*deferred: tuple[str, str]) -> str:
        if layout == "json":
            anchors = {"path": ["src/cli/**", "src/core/**"]}
            entries = [("path", value, reason) for value, reason in deferred]
            return guide(anchors=anchors, at=T0, because="first", deferred=entries)
        written = _deferred(*deferred) if deferred else ""
        return _page(T0, because="first", anchors=BOTH_ANCHORS, deferred=written)

    _merge(
        repo,
        {PAGE: page()},
        {PAGE: page(("src/cli/**", "cli"))},
        {PAGE: page(("src/core/**", "core"))},
    )

    result = _cli("--json")

    assert result.exit_code == 0, result.output
    assert _revalidated(repo)["deferred"] == [
        {"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "cli"},
        {"anchor": {"kind": "path", "value": "src/core/**"}, "reason": "core"},
    ]
    assert json.loads(result.output)["files"][0]["owed"] == []


# --- the base side's answer, and when it is not taken ----------------------------------


def test_a_merge_of_a_branch_that_is_not_the_check_base_leaves_two_revalidations(
    repo: AdopterRepo,
) -> None:
    """Merging another feature branch (or pulling a shared one): the change check's base is
    still `main`, so the other side's answer, taken, would read as a fresh revalidation of
    this branch's change that nobody made. The block is left to the person."""
    repo.write({CONFIG: friction_config(), **SOURCE, PAGE: ANCESTOR})
    repo.commit("ancestor")
    repo.checkout("other", create=True)
    repo.commit("the other branch", {PAGE: BASE})
    repo.checkout("main")
    repo.checkout("topic", create=True)
    repo.commit("this branch", {PAGE: THIS})
    merged = repo.git("merge", "-q", "--no-edit", "other", check=False)
    assert merged.returncode == 1, merged.stdout + merged.stderr
    conflicted = _read(repo)

    result = _cli()

    assert result.exit_code == 1, result.output
    other = repo.git("rev-parse", "other").stdout.strip()
    assert f"MERGE_HEAD {other[:12]} is not the change check's base (main at" in result.output
    assert "a revalidation made here, which nobody made" in result.output
    assert _read(repo) == conflicted
    assert _unmerged(repo) == {PAGE}


def test_both_sides_changing_the_answer_but_only_one_revalidating_is_left(
    repo: AdopterRepo,
) -> None:
    ancestor = _page(T0, because="first")
    this = _page(T0, because="first, reworded")  # `at` held: no revalidation
    _merge(repo, {PAGE: ancestor}, {PAGE: this}, {PAGE: BASE})

    result = _cli()

    assert result.exit_code == 1, result.output
    assert "only one changed `at`: no two revalidations to settle" in result.output
    assert _unmerged(repo) == {PAGE}


def test_one_anchors_deferral_changed_differently_on_both_sides_is_left(
    repo: AdopterRepo,
) -> None:
    ancestor = _page(T0, because="first")
    this = _page(T0, because="first", deferred=_deferred(("src/cli/**", "next week")))
    base = _page(T0, because="first", deferred=_deferred(("src/cli/**", "next month")))
    _merge(repo, {PAGE: ancestor}, {PAGE: this}, {PAGE: base})

    result = _cli()

    assert result.exit_code == 1, result.output
    assert f"the deferral of path:src/cli/** in {PAGE}, differently" in result.output
    assert _unmerged(repo) == {PAGE}


def test_a_block_the_base_side_removed_while_this_branch_changed_it_is_reported(
    repo: AdopterRepo,
) -> None:
    removed = ANCESTOR.replace(f"    revalidated:\n      at: {T0}\n      outcome: updated\n", "")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: removed})
    conflicted = _read(repo)

    result = _cli()

    assert result.exit_code == 1, result.output
    assert (
        f"the base side removed the `revalidated` block of {PAGE} and this branch changed it"
        in result.output
    )
    assert _read(repo) == conflicted


# --- left, skipped, nothing to do ----------------------------------------------------


def test_a_conflict_in_the_body_is_left_and_said(repo: AdopterRepo) -> None:
    this = _page(T0, "updated", None, body="The CLI takes two flags.\n")
    base = _page(T0, "updated", None, body="The CLI takes no flag.\n")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: base})
    conflicted = _read(repo)

    result = _cli()

    assert result.exit_code == 1, result.output
    assert f"{PAGE} — left in conflict: it conflicts in the body" in result.output
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
    assert "take the base side's answer" in result.output
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


def test_a_conflict_region_reaching_past_the_block_is_left(repo: AdopterRepo) -> None:
    """Only this branch changed the field below the block, but git's conflict region takes
    that line in with the block. The region lies partly outside the block, so the file is
    left — never re-merged where git conflicted."""
    this = THIS.replace("status: draft", "status: review")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: this}, {PAGE: BASE})
    conflicted = _read(repo)
    assert re.search(r"=======\n(.*\n)*status: draft\n>>>>>>> main", conflicted)

    result = _cli()

    assert result.exit_code == 1, result.output
    assert "it conflicts in the front matter, outside the `revalidated` blocks" in result.output
    assert _read(repo) == conflicted


def test_a_file_resolved_in_part_by_hand_is_never_overwritten(repo: AdopterRepo) -> None:
    """Two conflicts; the person resolved the first and left the second. The file is not
    git's conflict any more, so it is refused and left exactly as the person has it."""
    first = (T0, "first")
    _merge(
        repo,
        {TERMS: _terms(first, first)},
        {TERMS: _terms((T1, "this alpha"), (T1, "this beta"))},
        {TERMS: _terms((T2, "base alpha"), (T2, "base beta"))},
    )
    conflicted = _read(repo, TERMS)
    region = re.compile(r"<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> main\n", re.DOTALL)
    by_hand = region.sub(lambda m: m.group(2), conflicted, count=1)
    assert by_hand != conflicted and "<<<<<<<" in by_hand
    repo.write({TERMS: by_hand})

    result = _cli()

    assert result.exit_code == 1, result.output
    assert "it is not the conflict git left" in result.output
    assert _read(repo, TERMS) == by_hand
    assert _unmerged(repo) == {TERMS}


def test_without_the_histogram_diff_the_conflict_is_still_checked(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A git before 2.44 has no histogram diff for `merge-file`: the conflict it reproduces
    is still compared with the one git left, and a file that differs is refused."""
    monkeypatch.setattr(fres, "_HISTOGRAM", "--no-such-option")
    _merge(repo, {PAGE: ANCESTOR}, {PAGE: THIS}, {PAGE: BASE})
    repo.write({PAGE: _read(repo) + "\nA line added by hand.\n"})

    refused = _cli()

    assert refused.exit_code == 1, refused.output
    assert "this git, before 2.44, lacks the histogram diff" in refused.output
    repo.git("checkout", "-m", "--", PAGE)  # git's conflict back
    assert _cli().exit_code == 0
    assert _read(repo) == BASE


def test_a_file_that_is_not_an_artefacts_is_skipped(repo: AdopterRepo) -> None:
    _merge(
        repo,
        {PAGE: ANCESTOR},
        {PAGE: THIS, "src/cli/main.py": "print('this')\n"},
        {PAGE: BASE, "src/cli/main.py": "print('base')\n"},
    )
    named = _cli("docs/other.md", "--dry-run")
    assert "docs/other.md — skipped: not in conflict" in named.output

    result = _cli("--yes")

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
    assert f"{PAGE} — would be resolved" in result.output
    assert f"    -      at: {T1}\n" in result.output  # this branch's block goes
    assert "    -<<<<<<< HEAD\n" in result.output
    assert f"      at: {T2}\n" in result.output  # the base side's stays
    assert UNCHANGED_COMMAND in result.output
    assert "Dry run: nothing written." in result.output
    assert "git add" not in result.output
    assert _read(repo) == conflicted
    assert _unmerged(repo) == {PAGE}
    document = json.loads(_cli("--dry-run", "--json").output)
    assert document["dry_run"] is True and document["files"][0]["staged"] is False
    assert _cli("--dry-run", "--yes").exit_code == 2


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


# --- a run stopped partway -----------------------------------------------------------


def _two_files_in_conflict(repo: AdopterRepo) -> fres.Resolution:
    first = (T0, "first")
    _merge(
        repo,
        {PAGE: ANCESTOR, TERMS: _terms(first, first)},
        {PAGE: THIS, TERMS: _terms((T1, "this alpha"), first)},
        {PAGE: BASE, TERMS: _terms((T2, "base alpha"), first)},
    )
    resolution = fres.plan_resolve(repo.root)
    assert [r.path for r in resolution.resolved] == [PAGE, TERMS]
    return resolution


def test_a_write_stopped_partway_says_what_it_wrote(repo: AdopterRepo) -> None:
    resolution = _two_files_in_conflict(repo)
    repo.write({TERMS: _read(repo, TERMS) + "\nEdited meanwhile.\n"})

    with pytest.raises(fres.FrictionResolveError) as raised:
        fres.write(repo.root, resolution)

    message = raised.value.message
    assert f"{TERMS} was not written: {TERMS} changed since it was read" in message
    assert f"This run wrote {PAGE}, staging none" in message
    assert f"Not written: {TERMS}." in message
    assert "Nothing was written" not in message
    assert _read(repo) == BASE


def test_staging_stopped_partway_says_what_it_staged(repo: AdopterRepo) -> None:
    resolution = _two_files_in_conflict(repo)
    written = fres.write(repo.root, resolution)
    lock = repo.root / ".git" / "index.lock"
    lock.write_bytes(b"")

    with pytest.raises(fres.FrictionResolveError) as raised:
        fres.stage(repo.root, written)

    lock.unlink()
    message = raised.value.message
    assert message.startswith(f"staging {PAGE} failed:")
    assert f"This run wrote {PAGE}, {TERMS}, staging none" in message
    assert f"Not staged: {PAGE}, {TERMS} — `git add -- {PAGE} {TERMS}`" in message


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
    assert (page["status"], page["staged"], page["reason"]) == ("resolved", False, None)
    (owed,) = page["owed"]
    assert owed["artefact"] == "guide" and owed["location"] == PAGE
    assert owed["base_answer"] == {
        "at": T2,
        "outcome": "unchanged",
        "unchanged-because": "the base's rename keeps every flag",
    }
    assert owed["outcome"] == "unchanged" and owed["command"] == UNCHANGED_COMMAND
    assert _unmerged(repo) == {PAGE, "src/cli/main.py"}
