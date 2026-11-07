"""Every guide address a reference links names a guide README (ADR-069 point 2).

A reference under `.pkit/` links its guide at the tag `latest`,
`https://github.com/aleskalfas/project-kit/blob/latest/docs/<path>/README.md`.
No migration reaches a reference already installed, so a guide README that
moves or goes breaks that link in every version that shipped it. These tests
read every such address in the files under `.pkit/`, in the tree and at each
release tag, and fail on one that names no README in the tree's `docs/`. Each
tag holds the references it shipped, so a guide moved after an old release
linked it fails here, though nobody listed the old address (ADR-069, "Addresses
read from the tags").

**What is read.** Every file under `.pkit/`, where the references live: more than
ships, since its `project/` folders and scratchpad notes are read too, and
nothing outside it. In the tree, untracked files count and ignored ones do not,
for the addresses and for the READMEs alike. The tags read are the release tags,
`v<major>.<minor>.<patch>`, as `scripts/latest_tag.py` reads them (PRJ-004).

**What counts as an address.** A link into project-kit's `docs/` at a ref that
moves: `github.com/aleskalfas/project-kit/` then `blob/`, `tree/`, `raw/` or
`blame/`, or `raw.githubusercontent.com/aleskalfas/project-kit/`, with the host,
owner and repository in any case and with or without the scheme; then `latest/`
or `main/`, as a tag or a branch (`refs/tags/latest/`); then a path that is
`docs`, written so in any case, or under it. The path runs up to the first
space, quote, bracket, brace, parenthesis, backtick, backslash, bar or `$`, less
the punctuation (`.`, `,`, `;`, `:`, `!`, `?`) or emphasis marks (`*`, `_`, `~`)
that end it. A link at `main` is read since `main` moves as `latest` does. A
link at a version tag or a commit names text that never moves, and is not read.

**When it holds.** When its path, without its `#fragment` or `?query` and with
each `%xx` decoded, names a file called exactly `README.md` in the tree's
`docs/`. So a link to a guide's folder, or to a page inside it, fails: only the
README keeps its path (ADR-069 point 3), and a shipped page links nothing
unshipped but its guide's README (point 4). A fragment is not checked. A
template is no address: a segment that starts with a placeholder
(`docs/<area>/README.md`, `{area}`, `$AREA`) or a path holding a `%` that
encodes nothing (`docs/%s/`).

**The reading may only grow looser.** Each tag's text never changes, so reading
more forms as addresses, or holding them to more, could fail a tag nothing can
mend. Change the reading only to accept more. There is no list of exceptions: a
failure at a tag is mended in the tree, by keeping a README at the path it
names, and one whose path can hold no README goes to the maintainer.

**Where no release tag is present.** The tree's addresses are read in every
clone. A clone holding no release tag, such as a clone made without its tags,
reads none at the tags: the test of the tags skips there and says why. Under
GitHub Actions it fails instead, since CI's checkout fetches every tag
(`fetch-depth: 0`, which `test_checks_workflow.py` pins for each part), so CI
cannot skip it. A pull request built on a release's commit before the release-tag
workflow cuts its tag reads that release's references only in the tree.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

import pytest
from scripts import latest_tag

from tests.adopter_repo import GitRepo

REPO = Path(__file__).resolve().parents[1]

#: The folder whose files are read: the references, and the rest of `.pkit/`.
READ = ".pkit"

#: The release whose references first linked a guide (ADR-069, "The pilot"): a
#: reading of the tags that holds it and finds no address has missed it.
FIRST_LINKED = "v2.0.0"

#: What `git grep` keeps a line for: every line an address can sit on, and more.
_LINES = ("/latest/docs", "/main/docs")

# An address: project-kit's repository on GitHub, a view of a file, a ref that
# moves, then the path, up to a character no address holds.
_STOP = r"\s<>{}()\[\]\"'`\\|$"
_ADDRESS = re.compile(
    r"(?i:https?://)?"
    r"(?:(?i:(?:www\.)?github\.com/aleskalfas/project-kit)/(?:blob|tree|raw|blame)/"
    r"|(?i:raw\.githubusercontent\.com/aleskalfas/project-kit)/)"
    r"(?:refs/(?:tags|heads)/)?(?:latest|main)/"
    rf"(?P<path>[^{_STOP}]*)"
)

#: What ends a sentence or an emphasis after a bare address, never the address's own.
_TRAILING = ".,;:!?*_~"

#: A placeholder that starts a segment of a template's path.
_PLACEHOLDER = re.compile(r"<[\w.-]+>|\{[\w.-]*\}|\$\{?\w+\}?")

#: A `%` that encodes no character: a template's, such as `%s`.
_NOT_ENCODING = re.compile(r"%(?![0-9A-Fa-f]{2})")


@dataclass(frozen=True)
class GuideAddress:
    """An address into `docs/`, and where it was read."""

    #: The address as written.
    address: str
    #: The path in the repository it names, such as `docs/permissions/README.md`.
    target: str
    #: The file it was read from, relative to the repository's root.
    file: str
    line: int
    #: The release tag it was read at; None for the tree.
    version: str | None = None

    @property
    def where(self) -> str:
        return f"{self.version or 'the tree'} (line {self.line})"


def addresses_in(text: str) -> list[tuple[str, str]]:
    """Each address in `text`, as written, with the path it names."""
    found: list[tuple[str, str]] = []
    for match in _ADDRESS.finditer(text):
        raw = match["path"]
        if (not raw or raw.endswith("/")) and _PLACEHOLDER.match(text, match.end()):
            continue
        if _NOT_ENCODING.search(raw):
            continue
        path = raw.rstrip(_TRAILING)
        address = match[0][: len(match[0]) - (len(raw) - len(path))]
        # `docs` as written, as `git grep` finds it; the target is decoded.
        written = path.split("#", 1)[0].split("?", 1)[0].rstrip("/")
        if written.lower() == "docs" or written.lower().startswith("docs/"):
            found.append((address, unquote(written)))
    return found


def _git(root: Path, *args: str) -> str:
    """What `git <args>` prints. A failure of git, or anything it says on its
    standard error, such as a file it could not read, raises: no reading passes
    half read."""
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    # `git grep` exits 1 when no line matched.
    if completed.returncode not in (0, 1) or completed.stderr.strip():
        raise RuntimeError(f"git {args[0]} failed in {root}: {completed.stderr.strip()}")
    return completed.stdout


def _grep(root: Path, *revisions: str) -> str:
    """`git grep`'s lines under `.pkit/` that may hold an address, in the working
    tree or at `revisions`."""
    where = list(revisions) if revisions else ["--untracked"]
    lines = [arg for line in _LINES for arg in ("-e", line)]
    return _git(
        root, "grep", "--no-color", "-I", "-n", "-z", "-i", "-F", *lines, *where, "--", READ
    )


def _read(output: str, *, at_tags: bool) -> list[GuideAddress]:
    """The addresses on `git grep -z -n`'s lines: `<name>\\0<line>\\0<text>`, where a
    name read at a tag is `<tag>:<path>`. A tag name holds no colon."""
    found: list[GuideAddress] = []
    for record in output.split("\n"):
        if not record:
            continue
        name, line, text = record.split("\0", 2)
        version, file = name.split(":", 1) if at_tags else (None, name)
        for address, target in addresses_in(text):
            found.append(GuideAddress(address, target, file, int(line), version))
    return found


def read_tree(root: Path) -> list[GuideAddress]:
    """Every address in the files under `.pkit/` in the working tree."""
    return _read(_grep(root), at_tags=False)


def read_tags(root: Path, tags: Sequence[str]) -> list[GuideAddress]:
    """Every address in the files under `.pkit/` at each of `tags`, in one reading."""
    return _read(_grep(root, *tags), at_tags=True) if tags else []


def release_tags(root: Path) -> list[str]:
    """The repository's release tags, lowest version first. `latest`, a pre-release
    and any other tag are none."""
    listed = _git(root, "tag", "--list").split("\n")
    keyed = [(key, tag) for tag in listed if (key := latest_tag.release_key(tag)) is not None]
    return [tag for _, tag in sorted(keyed)]


def tags_to_read(root: Path, environ: Mapping[str, str]) -> list[str]:
    """The release tags to read; with none, a skip, or under GitHub Actions a failure."""
    tags = release_tags(root)
    if tags:
        return tags
    if environ.get("GITHUB_ACTIONS") == "true":
        pytest.fail(
            "This clone holds no release tag, so no guide address is read at the tags "
            "(ADR-069 point 2). CI's checkout must fetch every tag: keep `fetch-depth: 0` "
            "on the checkout of the job that runs this test."
        )
    pytest.skip(
        "This clone holds no release tag, so no guide address is read at the tags. "
        "Fetch them to run this test: git fetch origin 'refs/tags/v*:refs/tags/v*'"
    )


def guide_readmes(root: Path) -> frozenset[str]:
    """Every file called `README.md` in the tree's `docs/`, tracked or untracked and
    not ignored, by its path from the root."""
    listed = _git(
        root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "docs"
    )
    return frozenset(
        path
        for path in listed.split("\0")
        if path.rsplit("/", 1)[-1] == "README.md" and (root / path).is_file()
    )


def unresolved(addresses: Iterable[GuideAddress], readmes: frozenset[str]) -> list[GuideAddress]:
    """The addresses that name no README in `readmes`."""
    return [address for address in addresses if address.target not in readmes]


def report(broken: Sequence[GuideAddress]) -> str:
    """Each address that names no README, once per file, with each version it was
    read at and what mends it."""
    groups: dict[tuple[str, str, str], list[GuideAddress]] = {}
    for found in broken:
        groups.setdefault((found.address, found.target, found.file), []).append(found)
    lines = [
        f"{len(groups)} guide address(es) name no README in the tree's docs/ (ADR-069 point 2):"
    ]
    for (address, target, file), read in groups.items():
        readme = target.rsplit("/", 1)[-1] == "README.md"
        if not any(found.version for found in read):
            mend = "Only the tree links it: fix the link, or add the README it names."
        elif readme:
            mend = "A release links it, and its text never changes: keep a README at that path."
        else:
            mend = (
                "A release links it, and its text never changes, yet no README can stand "
                "at that path: take it to the maintainer."
            )
        lines += [
            f"- {address}",
            f"  names {target}, "
            + ("which the tree's docs/ does not hold" if readme else "which is no README"),
            f"  read in {file} at " + ", ".join(found.where for found in read),
            f"  {mend}",
        ]
    return "\n".join(lines)


def check_tree(root: Path) -> tuple[list[GuideAddress], str | None]:
    """The addresses read in the tree, and the report of those that name no README,
    or None where each names one."""
    read = read_tree(root)
    broken = unresolved(read, guide_readmes(root))
    return read, report(broken) if broken else None


def check_tags(
    root: Path, environ: Mapping[str, str]
) -> tuple[list[str], list[GuideAddress], str | None]:
    """The release tags read, the addresses read at them, and the report of those
    that name no README in the tree, or None where each names one."""
    tags = tags_to_read(root, environ)
    read = read_tags(root, tags)
    broken = unresolved(read, guide_readmes(root))
    return tags, read, report(broken) if broken else None


# --- project-kit's own addresses -----------------------------------------------


def test_every_guide_address_in_the_tree_names_a_guide_readme() -> None:
    read, failure = check_tree(REPO)
    assert read, (
        f"No guide address read under {READ}/ in the tree, though the permissions "
        "reference links its guide (ADR-069, 'The pilot'): the reading missed it."
    )
    assert failure is None, failure


def test_every_guide_address_at_each_release_tag_names_a_guide_readme() -> None:
    tags, read, failure = check_tags(REPO, os.environ)
    if FIRST_LINKED in tags:
        assert read, f"No guide address read at the tags, though {FIRST_LINKED} links one."
    assert failure is None, failure


# --- what counts as an address -------------------------------------------------

BASE = "https://github.com/aleskalfas/project-kit"
GUIDE = "docs/permissions/README.md"
PAGE = "docs/permissions/010-turn-on.md"


def _one(address: str, target: str = GUIDE) -> list[tuple[str, str]]:
    return [(address, target)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Where an address ends.
        (f"the [guide]({BASE}/blob/latest/{GUIDE}).", _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f"<{BASE}/blob/latest/{GUIDE}>", _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f"see {BASE}/blob/latest/{GUIDE}.", _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f"**{BASE}/blob/latest/{GUIDE}**", _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f'<a href="{BASE}/blob/latest/{GUIDE}">x</a>', _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f"{BASE}/blob/latest/{GUIDE}</a>", _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f"{BASE}/blob/latest/{GUIDE}<br>", _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f'"{BASE}/blob/latest/{GUIDE}\\n"', _one(f"{BASE}/blob/latest/{GUIDE}")),
        (f"|{BASE}/blob/latest/{GUIDE}|", _one(f"{BASE}/blob/latest/{GUIDE}")),
        (
            f"[x]({BASE}/blob/latest/{GUIDE}#turning-it-on)",
            _one(f"{BASE}/blob/latest/{GUIDE}#turning-it-on"),
        ),
        # The views, refs and hosts read.
        (
            f"HTTPS://GitHub.com/AlesKalfas/Project-Kit/tree/latest/{GUIDE}",
            _one(f"HTTPS://GitHub.com/AlesKalfas/Project-Kit/tree/latest/{GUIDE}"),
        ),
        (
            f"github.com/aleskalfas/project-kit/raw/latest/{GUIDE}",
            _one(f"github.com/aleskalfas/project-kit/raw/latest/{GUIDE}"),
        ),
        (f"{BASE}/blame/main/{GUIDE}", _one(f"{BASE}/blame/main/{GUIDE}")),
        (f"{BASE}/blob/refs/tags/latest/{GUIDE}", _one(f"{BASE}/blob/refs/tags/latest/{GUIDE}")),
        (
            f"https://raw.githubusercontent.com/aleskalfas/project-kit/latest/{GUIDE}",
            _one(f"https://raw.githubusercontent.com/aleskalfas/project-kit/latest/{GUIDE}"),
        ),
        # Read, and held to a README.
        (
            f"{BASE}/blob/latest/Docs/permissions/README.md",
            _one(f"{BASE}/blob/latest/Docs/permissions/README.md", "Docs/permissions/README.md"),
        ),
        (
            f"`{BASE}/tree/latest/docs/permissions/`",
            _one(f"{BASE}/tree/latest/docs/permissions/", "docs/permissions"),
        ),
        (f"({BASE}/blob/latest/{PAGE})", _one(f"{BASE}/blob/latest/{PAGE}", PAGE)),
        (f"{BASE}/blob/latest/docs", _one(f"{BASE}/blob/latest/docs", "docs")),
        # Templates.
        (f"`{BASE}/blob/latest/docs/<area>/README.md`", []),
        (f'f"{BASE}/blob/latest/docs/{{area}}/README.md"', []),
        (f'"{BASE}/blob/latest/docs/${{AREA}}/README.md"', []),
        (f'"{BASE}/blob/latest/docs/$area/README.md"', []),
        (f'"{BASE}/blob/latest/docs/%s/README.md" % area', []),
        # Not read.
        (f"{BASE}/blob/v2.0.0/{GUIDE}", []),
        (f"{BASE}/blob/524c9bef/{GUIDE}", []),
        (f"https://github.com/someone/project-kit/blob/latest/{GUIDE}", []),
        (f"{BASE}/blob/latest/README.md", []),
        (f"{BASE}/blob/main/.pkit/decisions/core/COR-049-documentation-roots.md", []),
        (f"{BASE}/blob/latest/docsy/README.md", []),
    ],
)
def test_what_counts_as_an_address(text: str, expected: list[tuple[str, str]]) -> None:
    assert addresses_in(text) == expected


def test_an_encoded_character_is_read_as_it_names() -> None:
    assert addresses_in(f"{BASE}/blob/latest/docs/permissions/READ%4DE.md") == [
        (f"{BASE}/blob/latest/docs/permissions/READ%4DE.md", GUIDE)
    ]
    # Only a `docs` written as such starts an address, as only it is on a line read.
    assert addresses_in(f"{BASE}/blob/latest/%64ocs/permissions/README.md") == []


def test_only_a_readme_in_the_tree_s_docs_resolves_an_address() -> None:
    readmes = frozenset({GUIDE, "docs/README.md"})
    found = [
        GuideAddress(address, target, ".pkit/x.md", 1)
        for text in (
            f"{BASE}/blob/latest/{GUIDE}#a-section",
            f"{BASE}/blob/latest/docs/README.md",
            f"{BASE}/tree/latest/docs/permissions",
            f"{BASE}/blob/latest/{PAGE}",
            f"{BASE}/blob/latest/docs/permissions/readme.md",
            f"{BASE}/blob/latest/Docs/permissions/README.md",
        )
        for address, target in addresses_in(text)
    ]
    assert [address.target for address in unresolved(found, readmes)] == [
        "docs/permissions",
        PAGE,
        "docs/permissions/readme.md",
        "Docs/permissions/README.md",
    ]


# --- the reading, in a repository of its own -----------------------------------


def _reference(*targets: str) -> str:
    links = "\n".join(f"- [the guide]({BASE}/blob/latest/{target})" for target in targets)
    return f"# A reference\n\n{links}\n"


@pytest.fixture
def scratch(tmp_path: Path) -> GitRepo:
    return GitRepo.init(tmp_path / "repo")


def test_it_fails_on_an_address_whose_readme_is_missing(scratch: GitRepo) -> None:
    scratch.commit(
        "A reference and one guide",
        {
            ".pkit/area/README.md": _reference("docs/area/README.md", "docs/gone/README.md"),
            "docs/area/README.md": "# The guide\n",
        },
    )

    read, failure = check_tree(scratch.root)

    gone = f"{BASE}/blob/latest/docs/gone/README.md"
    assert unresolved(read, guide_readmes(scratch.root)) == [
        GuideAddress(gone, "docs/gone/README.md", ".pkit/area/README.md", 4)
    ]
    assert failure is not None
    assert f"- {gone}\n" in failure
    assert "names docs/gone/README.md, which the tree's docs/ does not hold" in failure
    assert "read in .pkit/area/README.md at the tree (line 4)" in failure
    assert "Only the tree links it: fix the link, or add the README it names." in failure


def test_the_tree_s_reading_holds_untracked_files_and_leaves_out_ignored_ones(
    scratch: GitRepo,
) -> None:
    scratch.commit(
        "A guide, and what is ignored",
        {"docs/area/README.md": "# The guide\n", ".gitignore": "ignored/\n"},
    )
    scratch.write(
        {
            ".pkit/new/README.md": _reference("docs/new/README.md", "docs/other/README.md"),
            ".pkit/ignored/README.md": _reference("docs/ignored-link/README.md"),
            "docs/new/README.md": "# Written, not yet committed\n",
            "docs/ignored/README.md": "# Ignored\n",
        }
    )

    assert guide_readmes(scratch.root) == {"docs/area/README.md", "docs/new/README.md"}
    read, failure = check_tree(scratch.root)
    assert [(found.file, found.target) for found in read] == [
        (".pkit/new/README.md", "docs/new/README.md"),
        (".pkit/new/README.md", "docs/other/README.md"),
    ]
    assert failure is not None and "docs/other/README.md" in failure


def test_it_fails_on_an_address_read_only_at_a_release_tag(scratch: GitRepo) -> None:
    scratch.commit(
        "The first release",
        {".pkit/area/README.md": _reference("docs/old/README.md"), "docs/old/README.md": "# Old\n"},
    )
    scratch.git("tag", "-a", "v1.0.0", "-m", "v1.0.0")
    # The guide moves, and the tree's reference follows it: the tree is sound.
    scratch.commit(
        "The guide moves",
        {
            ".pkit/area/README.md": _reference("docs/new/README.md"),
            "docs/old/README.md": None,
            "docs/new/README.md": "# New\n",
        },
    )
    scratch.git("tag", "v1.1.0")
    assert check_tree(scratch.root)[1] is None

    tags, read, failure = check_tags(scratch.root, {})

    old = f"{BASE}/blob/latest/docs/old/README.md"
    assert tags == ["v1.0.0", "v1.1.0"]
    assert unresolved(read, guide_readmes(scratch.root)) == [
        GuideAddress(old, "docs/old/README.md", ".pkit/area/README.md", 3, "v1.0.0")
    ]
    assert failure is not None
    assert f"- {old}\n" in failure
    assert "read in .pkit/area/README.md at v1.0.0 (line 3)\n" in failure
    assert "A release links it, and its text never changes: keep a README at that path." in failure


def test_a_page_a_release_links_cannot_be_mended_by_a_readme(scratch: GitRepo) -> None:
    scratch.commit(
        "A release links a page",
        {".pkit/area/README.md": _reference(PAGE), PAGE: "# A page\n"},
    )
    scratch.git("tag", "v1.0.0")

    failure = check_tags(scratch.root, {})[2]

    assert failure is not None
    assert f"names {PAGE}, which is no README" in failure
    assert "no README can stand at that path: take it to the maintainer." in failure


def test_only_release_tags_are_read_lowest_first(scratch: GitRepo) -> None:
    scratch.commit("Start", {"README.md": "start\n"})
    for tag in ("v1.10.0", "v1.9.0", "latest", "other", "v1.0.0-rc.1", "v01.0.0", "vfoo"):
        scratch.git("tag", tag)

    assert release_tags(scratch.root) == ["v1.9.0", "v1.10.0"]


def test_a_reading_git_cannot_make_fails_rather_than_passing(scratch: GitRepo) -> None:
    scratch.commit("Start", {"README.md": "start\n"})

    with pytest.raises(RuntimeError, match="git grep failed"):
        read_tags(scratch.root, ["v9.9.9"])


def test_a_coloured_git_grep_is_read_all_the_same(scratch: GitRepo) -> None:
    scratch.commit("A reference", {".pkit/area/README.md": _reference("docs/area/README.md")})
    scratch.git("config", "color.ui", "always")
    scratch.git("config", "color.grep", "always")

    assert [found.target for found in read_tree(scratch.root)] == ["docs/area/README.md"]


# --- where no release tag is present -------------------------------------------


def test_with_no_release_tag_it_skips_outside_ci(scratch: GitRepo) -> None:
    scratch.commit("Start", {"README.md": "start\n"})
    scratch.git("tag", "latest")

    with pytest.raises(pytest.skip.Exception, match=re.escape("refs/tags/v*:refs/tags/v*")):
        tags_to_read(scratch.root, {})


def test_with_no_release_tag_it_fails_under_github_actions(scratch: GitRepo) -> None:
    scratch.commit("Start", {"README.md": "start\n"})

    with pytest.raises(pytest.fail.Exception, match="fetch-depth: 0"):
        tags_to_read(scratch.root, {"GITHUB_ACTIONS": "true"})


def test_with_a_release_tag_it_reads_them_in_ci_and_out(scratch: GitRepo) -> None:
    scratch.commit("Start", {"README.md": "start\n"})
    scratch.git("tag", "v1.0.0")

    assert tags_to_read(scratch.root, {}) == ["v1.0.0"]
    assert tags_to_read(scratch.root, {"GITHUB_ACTIONS": "true"}) == ["v1.0.0"]
