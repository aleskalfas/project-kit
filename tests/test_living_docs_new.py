"""living-docs' authoring command: a page, and a space's definition (#1617).

`pkit living-docs new page` and `new space` (DEC-001 points 2 and 4), run as the
backbone runs a capability's command, over an adopter repository with the
capability installed (the fixture of `test_living_docs_spaces.py`):

- **a page** — stamped into each root and into a place outside the roots that
  is assigned to a space, with its reader, kind and anchors, a guide with its
  parts in order (living-docs DEC-003); refused, with
  nothing written, for a space or kind the project lacks, a file that exists, a
  path that is no Markdown file of the repository or is reached through a link,
  a reader that is not a word and a title validation does not read; refused
  after the write, with the file put back, where the validator's own check says
  it is no page of the space or brings an error the project did not have — a
  file under the other root or in the definitions location, a place whose
  definition's scope misses it, a tie between two places, a reader the readers
  point does not hold;
- **what the check cannot read** — where the rules bind unreadable before the
  write refuses it, and after the write puts the page back; a failed recording
  of the definitions location, and an interruption of the check, put a space's
  files back;
- **a space** — the user space's definition written with its one rule and the
  technical space's without, a space the project adds declared by its entry,
  the configuration's every other byte kept, CRLF and a byte-order mark
  included, a missing configuration created and the definitions location
  recorded the first time; refused for a space that has a definition, a set name
  taken, roots that are one folder, a configuration the stamp cannot edit as
  text, and, after the write, an untyped place outside the roots and a
  place of another space the new scope also covers; the pages the space's
  rules then fail reported, never refused;
- **both, filled** — a space and a page the command created, once the page's
  placeholders are filled, pass the validator, the backbone's rule-set and
  friction passes, with `LDOC`'s rules binding on the page through the new
  definition.

Each dry run writes nothing.

The command's `main` runs in the test's own process, off a terminal, and every
`pkit` it calls is answered by the backbone's CLI in this process too
(`tests/in_process.py`). Two tests keep a real process, each marked with why:
the space form's and the page form's end-to-end tests. There the `pkit` the
script calls is the real CLI under this interpreter (`pkit_on_path`), so no test
reaches `uv` or the network.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.in_process import InProcessPkit, load, route_pkit, run_main
from tests.test_living_docs_spaces import (
    CONFIG,
    DEFINITIONS,
    LD,
    LD_CONFIG,
    PAGE,
    _definition,
    declare,
    errors,
    run,
)

NEW = LD / "scripts" / "new.py"

LOCATIONS = f"{LD.as_posix()}/project/docs-locations.yaml"

#: The top-level README as a place outside the roots that gives the page type, as a
#: place assigned to a space whose definition selects by type gives it (DEC-001 point 1).
README: Any = {"path": "README.md", "type": "living-docs:page"}

#: The spaces of a project that has created none yet: each names its entry point only.
UNDEFINED = {
    "user": {"entry-point": "README.md"},
    "technical": {"entry-point": "tech-docs/README.md"},
}


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """An adopter with living-docs installed, two separate roots, one page per
    space's entry, a decision record, and both spaces' definitions — clean."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    declare(repo)
    repo.write(
        {
            "README.md": PAGE,
            "docs/guide.md": PAGE,
            "tech-docs/README.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# Tech\n",
            f"{DEFINITIONS}/user.md": _definition("USER"),
            f"{DEFINITIONS}/technical.md": _definition("TECH"),
        }
    )
    return repo


@pytest.fixture
def fresh(project: AdopterRepo) -> AdopterRepo:
    """The same project before it created its spaces: no definition, none named, and
    its place outside the roots typed, as a definition that selects by type asks."""
    declare(project, places=[README], spaces=UNDEFINED)
    project.write({f"{DEFINITIONS}/user.md": None, f"{DEFINITIONS}/technical.md": None})
    return project


def new(
    repo: AdopterRepo, *args: str, in_a_process: bool = False
) -> subprocess.CompletedProcess[str]:
    """`pkit living-docs new …`, as the backbone runs it, off a terminal: its `main` in
    this process from the repository's root, standard input no terminal, every `pkit` it
    calls answered here too. `in_a_process` runs the adopter's copy of the script as a
    process of its own instead, its standard input empty, for a test marked `process`."""
    if in_a_process:
        return subprocess.run(
            [sys.executable, str(repo.root / NEW), *args],
            cwd=repo.root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    script, backbone = load("living-docs", "new.py", "backbone")
    with pytest.MonkeyPatch.context() as patched:
        route_pkit(patched, backbone)
        patched.setattr(sys, "stdin", io.StringIO())
        return run_main(script, *args, cwd=repo.root)


def page(
    repo: AdopterRepo, file: str, *args: str, dry_run: bool = False, in_a_process: bool = False
) -> subprocess.CompletedProcess[str]:
    """A page stamp with the space, reader, kind and title a test does not care about."""
    defaults = {"--space": "user", "--kind": "signpost", "--reader": "user", "--title": "Guide"}
    given = dict(zip(args[::2], args[1::2], strict=True))
    flags = [part for key, value in {**defaults, **given}.items() for part in (key, value)]
    dry = ["--dry-run"] if dry_run else []
    return new(repo, "page", file, *flags, *dry, in_a_process=in_a_process)


def probe(repo: AdopterRepo, case: str) -> str:
    """How a stamp ended in `case`, with one of its readings made to fail as the command
    would meet it: the stamp's own functions called in this process, from the repository's
    root, every `pkit` they call answered here too. What the stamp prints, and how it
    ended, are the lines returned."""
    stamp, binding, backbone = load("living-docs", "stamp", "binding", "backbone")
    root = repo.root
    calls: list[Path] = []

    def flaky(error: BaseException | None) -> Callable[[Path], Any]:
        def reach(at: Path) -> Any:
            calls.append(at)
            if error is not None and len(calls) > (0 if case == "unread-before" else 1):
                raise error
            return binding.read_binding(at)

        return reach

    def fail(_root: Path) -> None:
        raise stamp.NotRecorded("the backbone could not write it")

    def answered(code: int) -> Callable[..., subprocess.CompletedProcess[str]]:
        def run(argv: list[str], **_options: Any) -> subprocess.CompletedProcess[str]:
            print(" ".join(argv))
            return subprocess.CompletedProcess(argv, code)

        return run

    page = stamp.PageRequest("docs/new.md", "user", "signpost", "user", "New")
    out = io.StringIO()
    with pytest.MonkeyPatch.context() as patched, contextlib.redirect_stdout(out):
        route_pkit(patched, backbone)
        try:
            if case in ("asked", "declined"):
                stamp.separate_roots(
                    root,
                    "user",
                    stamp.Separation(),
                    rerun="pkit living-docs new space user",
                    run=answered(0 if case == "asked" else 1),
                    interactive=lambda: True,
                )
            elif case in ("unread-before", "unread-after"):
                stamp.stamp_page(root, page, reach=flaky(binding.Unreadable("no answer")))
            elif case == "interrupted":
                stamp.stamp_space(
                    root, stamp.SpaceRequest("user"), reach=flaky(KeyboardInterrupt())
                )
            elif case == "record-fails":
                stamp.stamp_space(
                    root, stamp.SpaceRequest("user"), record=fail, is_recorded=lambda _root: False
                )
        except stamp.Refused as exc:
            print(f"refused: {exc}")
        except KeyboardInterrupt:
            print("interrupted")
        else:
            print("stamped")
    return out.getvalue().strip()


def refused(completed: subprocess.CompletedProcess[str]) -> str:
    assert completed.returncode == 1, (completed.stdout, completed.stderr)
    assert completed.stderr.startswith("refused: "), completed.stderr
    return completed.stderr


def stamped(completed: subprocess.CompletedProcess[str]) -> str:
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def front(repo: AdopterRepo, rel: str) -> Mapping[str, Any]:
    from ruamel.yaml import YAML

    _, head, _body = (repo.root / rel).read_text(encoding="utf-8").split("---\n", 2)
    return YAML(typ="safe").load(head)


def snapshot(repo: AdopterRepo) -> dict[str, bytes]:
    """Every file of the working tree outside `.git`, with its bytes: what running a
    script leaves besides, its compiled modules, left out."""
    return {
        path.relative_to(repo.root).as_posix(): path.read_bytes()
        for path in sorted(repo.root.rglob("*"))
        if path.is_file() and not {".git", "__pycache__"} & set(path.relative_to(repo.root).parts)
    }


# --- a page --------------------------------------------------------------------------------------


def test_a_page_is_stamped_into_each_root_and_an_assigned_place(project: AdopterRepo) -> None:
    declare(
        project,
        places=["README.md", "guides/**"],
        assignments={"README.md": "user", "guides/**": "user"},
    )
    scope = ["docs/**", "README.md", "guides/**"]
    project.write({f"{DEFINITIONS}/user.md": _definition("USER", scope=scope)})
    out = stamped(
        page(
            project,
            "docs/install.md",
            "--kind",
            "reference",
            "--title",
            "Installing",
            "--path",
            "src/install.py",
            "--record",
            "living-docs:DEC-001#4",
        )
    )
    assert out.splitlines()[0] == (
        "stamped docs/install.md: a reference page of space 'user', for reader 'user'."
    )
    assert front(project, "docs/install.md") == {
        "reader": "user",
        "kind": "reference",
        "pkit": {
            "friction": {
                "anchors": {"path": ["src/install.py"], "record": ["living-docs:DEC-001#4"]}
            }
        },
    }
    body = (project.root / "docs/install.md").read_text(encoding="utf-8")
    assert "\n# Installing\n" in body and "# <Surface>" not in body
    stamped(page(project, "tech-docs/design.md", "--space", "technical", "--reader", "maintainer"))
    assert front(project, "tech-docs/design.md")["pkit"] == {"friction": {}}
    stamped(page(project, "guides/first.md", "--space", "user"))
    assert errors(run(project)) == []


@pytest.mark.process(
    "the page form's end-to-end test: the command as a process of its own, its exit code "
    "and the notes a person reads, and the pkit it starts"
)
def test_the_stamp_lists_the_template_placeholders_left_and_never_a_title_of_its_own(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    title = "Map<K, V> reference"
    out = stamped(page(project, "docs/maps.md", "--title", title, in_a_process=True))
    assert f"\n# {title}\n" in (project.root / "docs/maps.md").read_text(encoding="utf-8")
    listed = [line.strip() for line in out.splitlines() if line.startswith("  docs/maps.md:")]
    assert listed == [
        "docs/maps.md:10: <One sentence: what this folder is for, for this reader.>",
        "docs/maps.md:12: - [<entry>](<entry>) — <what the reader finds there, in a line>.",
    ]
    assert "run `pkit living-docs validate`, `pkit validate` and `pkit friction check`" in out


def test_a_guide_is_stamped_with_its_parts_in_order_and_checked_for_its_title(
    project: AdopterRepo,
) -> None:
    """The guide's template shows its parts in their order (living-docs DEC-003 point
    2): the stamp writes them under the title given and lists each one the writer
    words. Its structure is its title alone (point 4), so the page passes validation
    before its other sections are worded."""
    out = stamped(page(project, "docs/turning-on.md", "--kind", "guide", "--title", "Turning on"))
    assert out.splitlines()[0] == (
        "stamped docs/turning-on.md: a guide page of space 'user', for reader 'user'."
    )
    assert front(project, "docs/turning-on.md") == {
        "reader": "user",
        "kind": "guide",
        "pkit": {"friction": {}},
    }
    text = (project.root / "docs/turning-on.md").read_text(encoding="utf-8")
    parts = [
        "## <Why the subject exists>",
        "## <A task the reader does>",
        "## <The folder's pages>",
    ]
    assert [line for line in text.splitlines() if line.startswith("#")] == [
        "# Turning on",
        *parts,
    ]
    listed = [line.split(": ", 1)[1] for line in out.splitlines() if "docs/turning-on.md:" in line]
    assert [line for line in listed if line.startswith("#")] == parts
    assert errors(run(project)) == []


@pytest.mark.parametrize(
    ("file", "args", "said"),
    [
        ("docs/new.md", ("--space", "readers"), "space 'readers' is not a space of this project"),
        ("docs/new.md", ("--kind", "tutorial"), "kind 'tutorial' is not one living-docs declares"),
        ("docs/guide.md", (), "docs/guide.md exists already"),
        ("docs/new.txt", (), "does not end `.md`"),
        ("../new.md", (), "leads outside the repository"),
        ("/tmp/new.md", (), "is not a path from the repository root"),
        ("docs/new.md", ("--reader", "User"), "--reader 'User' is not a reader's id"),
        ("docs/new.md", ("--title", "<Folder>"), "is not a title validation reads"),
        ("docs/new.md", ("--title", " "), "is not a title validation reads"),
    ],
)
def test_a_page_is_refused_before_the_write(
    project: AdopterRepo, file: str, args: tuple[str, ...], said: str
) -> None:
    before = snapshot(project)
    assert said in refused(page(project, file, "--space", "user", *args))
    assert snapshot(project) == before


def test_a_page_reached_through_a_link_is_refused(project: AdopterRepo, tmp_path: Path) -> None:
    elsewhere = tmp_path.parent / f"{tmp_path.name}-elsewhere"
    elsewhere.mkdir()
    (project.root / "docs/linked").symlink_to(elsewhere, target_is_directory=True)
    message = refused(page(project, "docs/linked/new.md", "--space", "user"))
    assert "is reached through the link docs/linked" in message
    assert list(elsewhere.iterdir()) == []


@pytest.mark.parametrize(
    ("file", "space", "said"),
    [
        ("tech-docs/new.md", "user", "would be a page of space 'technical'"),
        (
            "tech-docs/living-docs/new.md",
            "technical",
            "an artefact of living-docs's definitions location",
        ),
    ],
)
def test_a_file_the_check_reads_as_no_page_of_the_space_is_put_back(
    project: AdopterRepo, file: str, space: str, said: str
) -> None:
    before = snapshot(project)
    message = refused(page(project, file, "--space", space))
    assert f"{file} would not be a page of space {space!r}" in message and said in message
    assert snapshot(project) == before


def test_a_page_its_place_assigns_outside_the_definitions_scope_is_put_back(
    project: AdopterRepo,
) -> None:
    declare(
        project,
        places=["README.md", "notes/**"],
        assignments={"README.md": "user", "notes/**": "user"},
    )
    before = snapshot(project)
    message = refused(page(project, "notes/today.md", "--space", "user"))
    assert "would bring validation errors the project did not have" in message
    assert "place 'notes/**' is assigned to space 'user'" in message
    assert snapshot(project) == before


def test_a_page_in_an_unassigned_place_of_rule_sets_outside_the_roots_is_put_back(
    project: AdopterRepo,
) -> None:
    """Such a place gives no space until it is assigned one (DEC-001 point 1)."""
    declare(project, places=["README.md", "old-docs/rule-sets"])
    project.write(
        {"old-docs/rule-sets/old.md": "---\nrule-set: OLD\nversion: 1.0.0\nrules: {}\n---\n"}
    )
    before = snapshot(project)
    message = refused(page(project, "old-docs/rule-sets/README.md", "--space", "user"))
    assert "old-docs/rule-sets/README.md would not be a page of space 'user'" in message
    assert (
        "it lies in no place of a space, and in project place 'old-docs/rule-sets', which is "
        "declared to hold rule sets, gives no type, lies outside every documentation root and "
        "is assigned to no space, so no space counts it"
    ) in message
    assert snapshot(project) == before


def test_a_page_two_places_claim_at_equal_rank_is_put_back(project: AdopterRepo) -> None:
    declare(
        project,
        places=["README.md", "notes/*.md", "notes/[ab].md"],
        assignments={"README.md": "user", "notes/*.md": "user", "notes/[ab].md": "user"},
    )
    scope = ["docs/**", "README.md", "notes/**"]
    project.write({f"{DEFINITIONS}/user.md": _definition("USER", scope=scope)})
    before = snapshot(project)
    message = refused(page(project, "notes/a.md", "--space", "user"))
    assert f"{CONFIG}:/friction/places/2" in message and "at equal rank" in message
    assert snapshot(project) == before


def test_a_page_for_a_reader_the_point_does_not_hold_is_put_back(project: AdopterRepo) -> None:
    before = snapshot(project)
    message = refused(page(project, "docs/new.md", "--space", "user", "--reader", "guest"))
    assert "docs/new.md:/reader" in message and "reader 'guest', which does not resolve" in message
    assert snapshot(project) == before


def test_a_page_dry_run_writes_nothing_and_warns_of_a_space_with_no_definition(
    fresh: AdopterRepo,
) -> None:
    before = snapshot(fresh)
    completed = page(fresh, "docs/new.md", dry_run=True)
    out = stamped(completed)
    assert out.startswith("would write docs/new.md:\n---\nreader: user\nkind: signpost\n")
    assert "dry run: nothing written" in out
    assert "space 'user' has no definition yet" in completed.stderr
    assert "`pkit living-docs new space user`" in completed.stderr
    assert snapshot(fresh) == before


# --- what the check cannot read ------------------------------------------------------------------


@pytest.mark.parametrize("case", ["unread-before", "unread-after"])
def test_where_the_rules_bind_unread_refuses_the_page_and_puts_it_back(
    fresh: AdopterRepo, case: str
) -> None:
    before = snapshot(fresh)
    ended = probe(fresh, case)
    when = "before" if case == "unread-before" else "after"
    assert ended.startswith(f"refused: {when} the write, the check cannot read all it judges: ")
    assert "`pkit rule-sets reach --json`" in ended
    assert snapshot(fresh) == before


@pytest.mark.parametrize(
    ("case", "ended"),
    [
        (
            "record-fails",
            "refused: the definitions location could not be recorded: the backbone could not "
            "write it; nothing is written",
        ),
        ("interrupted", "interrupted"),
    ],
)
def test_a_failed_recording_or_an_interruption_puts_the_space_back(
    fresh: AdopterRepo, case: str, ended: str
) -> None:
    before = snapshot(fresh)
    assert probe(fresh, case) == ended
    assert snapshot(fresh) == before


# --- a space -------------------------------------------------------------------------------------


def test_the_user_space_is_written_with_its_rule_and_the_location_recorded(
    fresh: AdopterRepo,
) -> None:
    assert not (fresh.root / LOCATIONS).exists() or "definitions" not in (
        fresh.root / LOCATIONS
    ).read_text(encoding="utf-8")
    out = stamped(new(fresh, "space", "user"))
    rel = f"{DEFINITIONS}/user.md"
    assert out.splitlines()[0] == (
        f"stamped {rel}: the definition of space 'user', rule set USER, inheriting "
        "living-docs:LDOC@1, scoped to the space's pages (docs/**, README.md)."
    )
    assert "recorded living-docs definitions = tech-docs/living-docs" in out
    assert "RS-USER-001, reader paths stay unbroken, is written accepted" in out
    assert front(fresh, rel) == {
        "rule-set": "USER",
        "version": "1.0.0",
        "inherits": ["living-docs:LDOC@1"],
        "scope": {"paths": ["docs/**", "README.md"], "types": ["living-docs:page"]},
        "rules": {
            "RS-USER-001": {
                "status": "accepted",
                "origin": {"decision": "living-docs:DEC-001"},
                "pkit": {"friction": {"anchors": {"record": ["living-docs:DEC-001#3"]}}},
            }
        },
    }
    text = (fresh.root / rel).read_text(encoding="utf-8")
    assert "# The user space's definition" in text
    assert text.endswith(
        "\n## RS-USER-001 — Reader paths stay unbroken\n\n"
        "The paths the user space's readers take through its pages stay unbroken.\n"
    )
    assert "definitions: tech-docs/living-docs" in (fresh.root / LOCATIONS).read_text(
        encoding="utf-8"
    )

    out = stamped(new(fresh, "space", "technical"))
    assert "recorded" not in out
    technical = front(fresh, f"{DEFINITIONS}/technical.md")
    assert (technical["rule-set"], technical["rules"]) == ("TECHNICAL", {})
    assert technical["scope"] == {"paths": ["tech-docs/**"], "types": ["living-docs:page"]}
    from ruamel.yaml import YAML

    config = YAML(typ="safe").load((fresh.root / LD_CONFIG).read_text(encoding="utf-8"))
    assert config["spaces"] == {
        "user": {"entry-point": "README.md", "definition": rel},
        "technical": {
            "entry-point": "tech-docs/README.md",
            "definition": f"{DEFINITIONS}/technical.md",
        },
    }
    assert errors(run(fresh)) == []
    result = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "rule-sets"])
    assert result.exit_code == 0, result.output


def test_the_configuration_keeps_every_other_byte_crlf_included(fresh: AdopterRepo) -> None:
    written = (
        "# our configuration\r\n"
        "pkit_schema: living-docs:config\r\n"
        "schema_version: 1\r\n"
        "\r\n"
        "spaces:\r\n"
        "    user:\r\n"
        "        entry-point: README.md   # where users start\r\n"
        "    technical:\r\n"
        "        entry-point: tech-docs/README.md\r\n"
        "\r\n"
        "# out-of-root places\r\n"
        "places:\r\n"
        "    README.md: user\r\n"
    )
    (fresh.root / LD_CONFIG).write_bytes(written.encode("utf-8"))
    stamped(new(fresh, "space", "user"))
    assert (fresh.root / LD_CONFIG).read_bytes() == written.replace(
        "README.md   # where users start\r\n",
        f"README.md   # where users start\r\n        definition: {DEFINITIONS}/user.md\r\n",
    ).encode("utf-8")


def test_a_byte_order_mark_is_kept(fresh: AdopterRepo) -> None:
    written = (fresh.root / LD_CONFIG).read_bytes()
    (fresh.root / LD_CONFIG).write_bytes(b"\xef\xbb\xbf" + written)
    stamped(new(fresh, "space", "technical"))
    assert (fresh.root / LD_CONFIG).read_bytes().startswith(b"\xef\xbb\xbfpkit_schema:")


@pytest.mark.parametrize(
    ("written", "said"),
    [
        (
            "pkit_schema: living-docs:config\nschema_version: 1\n"
            "spaces: {user: {entry-point: README.md}}\n",
            f"add `definition: {DEFINITIONS}/user.md` under `spaces.user` there by hand",
        ),
        (
            "pkit_schema: living-docs:config\r\nschema_version: 1\n",
            "it has mixed line endings",
        ),
        ("pkit_schema: living-docs:config\rschema_version: 1\r", "its lines end a lone CR"),
    ],
)
def test_a_configuration_the_stamp_cannot_edit_as_text_is_refused(
    fresh: AdopterRepo, written: str, said: str
) -> None:
    (fresh.root / LD_CONFIG).write_bytes(written.encode("utf-8"))
    before = snapshot(fresh)
    assert said in refused(new(fresh, "space", "user"))
    assert snapshot(fresh) == before


def test_a_missing_configuration_is_created(fresh: AdopterRepo) -> None:
    declare(fresh, places=[], assignments={}, spaces={})
    (fresh.root / LD_CONFIG).unlink()
    stamped(new(fresh, "space", "user"))
    assert (fresh.root / LD_CONFIG).read_text(encoding="utf-8") == (
        "pkit_schema: living-docs:config\nschema_version: 1\n\n"
        f"spaces:\n  user:\n    definition: {DEFINITIONS}/user.md\n"
    )
    assert front(fresh, f"{DEFINITIONS}/user.md")["scope"]["paths"] == ["docs/**"]


def test_a_space_the_project_adds_is_declared_by_its_entry(fresh: AdopterRepo) -> None:
    api: Any = {"path": "api/**", "type": "living-docs:page"}
    declare(
        fresh,
        places=[README, api],
        assignments={"README.md": "user", "api/**": "api"},
        spaces=UNDEFINED,
    )
    out = stamped(new(fresh, "space", "api"))
    assert "which declares the space." in out
    assert front(fresh, f"{DEFINITIONS}/api.md")["scope"] == {
        "paths": ["api/**"],
        "types": ["living-docs:page"],
    }
    stamped(page(fresh, "api/endpoints.md", "--space", "api", "--kind", "reference"))
    reach = InProcessPkit()(
        ["pkit", "rule-sets", "reach", "--json"],
        cwd=fresh.root,
        capture_output=True,
        text=True,
        check=True,
    )
    (entry,) = [a for a in json.loads(reach.stdout)["artefacts"] if a["path"] == "api/endpoints.md"]
    assert "living-docs:RS-LDOC-003" in {rule["rule"] for rule in entry["rules"]}


def test_the_pages_the_space_s_rules_then_fail_are_reported_and_the_space_stands(
    fresh: AdopterRepo,
) -> None:
    fresh.write({"docs/guide.md": "---\nreader: guest\nkind: signpost\n---\n\n# Guide\n"})
    completed = new(fresh, "space", "user")
    stamped(completed)
    assert "the space's rules now bind on its pages, and validation fails" in completed.stderr
    assert "docs/guide.md:/reader" in completed.stderr
    assert (fresh.root / DEFINITIONS / "user.md").is_file()


@pytest.mark.parametrize(
    ("args", "said"),
    [
        (("user",), f"space 'user' exists: {LD_CONFIG} names its definition"),
        (("api", "--set", "TECH"), f"rule set TECH is declared already, by {DEFINITIONS}/tech"),
        (("API",), "the space 'API' is not a space's id"),
        (("api", "--set", "api"), "--set 'api' is not a rule set's name"),
    ],
)
def test_a_space_is_refused_before_the_write(
    project: AdopterRepo, args: tuple[str, ...], said: str
) -> None:
    before = snapshot(project)
    assert said in refused(new(project, "space", *args))
    assert snapshot(project) == before


def test_a_definition_on_disk_the_configuration_does_not_name_is_refused(
    project: AdopterRepo,
) -> None:
    declare(project, spaces=UNDEFINED)
    before = snapshot(project)
    message = refused(new(project, "space", "user"))
    assert f"{DEFINITIONS}/user.md exists already" in message
    assert snapshot(project) == before


def test_a_space_the_project_adds_sets_the_roots_apart_and_a_page_of_it_does_not(
    fresh: AdopterRepo,
) -> None:
    """Every definition lies in the technical space, but a page of a space the project adds
    lies in its own places (DEC-001 points 1 and 2)."""
    api: Any = {"path": "api/**", "type": "living-docs:page"}
    declare(
        fresh,
        roots={"user": "docs/", "internal": "docs/"},
        places=[README, api],
        assignments={"README.md": "user", "api/**": "api"},
        spaces=UNDEFINED,
    )
    assert "The two documentation roots are one folder" in refused(new(fresh, "space", "api"))
    flags = ("--space", "api", "--kind", "reference", "--reader", "user", "--title", "API")
    message = refused(new(fresh, "page", "api/x.md", *flags, "--internal-root", "handbook"))
    assert "a page of space 'api' lies in places of its own" in message
    out = stamped(new(fresh, "space", "api", "--yes"))
    assert "set docs.internal = tech-docs" in out
    assert front(fresh, f"{DEFINITIONS}/api.md")["scope"]["paths"] == ["api/**"]


def test_an_untyped_place_outside_the_roots_is_put_back(fresh: AdopterRepo) -> None:
    declare(
        fresh,
        places=[README, "guides/**"],
        assignments={"README.md": "user", "guides/**": "user"},
        spaces=UNDEFINED,
    )
    before = snapshot(fresh)
    message = refused(new(fresh, "space", "user"))
    assert "would bring validation errors the project did not have" in message
    assert "project place 'guides/**' lies outside every documentation root" in message
    assert snapshot(fresh) == before


def test_a_place_of_another_space_the_new_scope_covers_is_put_back(project: AdopterRepo) -> None:
    api: Any = {"path": "api/**", "type": "living-docs:page"}
    internal: Any = {"path": "api/internal.md", "type": "living-docs:page"}
    declare(
        project,
        places=["README.md", api, internal],
        assignments={"README.md": "user", "api/**": "api", "api/internal.md": "technical"},
    )
    scope = ["tech-docs/**", "api/internal.md"]
    project.write(
        {
            f"{DEFINITIONS}/technical.md": _definition("TECH", scope=scope),
            "api/internal.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# Internal\n",
        }
    )
    before = snapshot(project)
    message = refused(new(project, "space", "api"))
    assert "which the scope of space 'api''s definition" in message
    assert "leave the place out of that scope with its `exclude`" in message
    assert snapshot(project) == before


def test_a_root_that_is_the_repository_is_scoped_as_everything_but_the_nested_root(
    fresh: AdopterRepo,
) -> None:
    declare(
        fresh,
        roots={"user": ".", "internal": "tech-docs/"},
        places=[],
        assignments={},
        spaces=UNDEFINED,
    )
    out = stamped(new(fresh, "space", "user", "--dry-run"))
    assert "  paths: ['**']\n  exclude: [tech-docs/**]\n" in out


def test_a_space_dry_run_prints_both_files_and_writes_nothing(fresh: AdopterRepo) -> None:
    before = snapshot(fresh)
    out = stamped(new(fresh, "space", "user", "--dry-run"))
    assert f"would write {DEFINITIONS}/user.md:\n---\nrule-set: USER\n" in out
    assert f"would write {LD_CONFIG}:\n" in out
    assert "It would record the definitions location, tech-docs/living-docs" in out
    assert snapshot(fresh) == before


# --- roots that are one folder (#2084) ------------------------------------------------------------

#: The two roots of a fresh project: one folder, as both default (COR-049 point 1).
SHARED = {"user": "docs/", "internal": "docs/"}

#: What the stamp says before the backbone's configuration command runs.
WHY = (
    "The two documentation roots are one folder, 'docs', and living-docs keeps the user and "
    "technical spaces apart (DEC-001 point 1). The internal root goes to 'tech-docs' first, "
    "outside the user root."
)


@pytest.fixture
def shared(fresh: AdopterRepo) -> AdopterRepo:
    """The fresh project with its two roots one folder."""
    declare(fresh, roots=SHARED, places=[README], spaces=UNDEFINED)
    return fresh


def _internal_root(repo: AdopterRepo) -> Any:
    from ruamel.yaml import YAML

    return YAML(typ="safe").load((repo.root / CONFIG).read_text(encoding="utf-8"))["docs"]


@pytest.mark.process(
    "the space form's end-to-end test: the stamp's own line and the output of the pkit "
    "config set it starts share one standard output, in order, across two processes"
)
def test_roots_that_are_one_folder_are_set_apart_before_the_space(
    shared: AdopterRepo, pkit_on_path: Path
) -> None:
    out = stamped(new(shared, "space", "user", "--yes", in_a_process=True))
    assert out.startswith(f"{WHY}\nset docs.internal = tech-docs  (.pkit/project/config.yaml)\n")
    assert _internal_root(shared) == {"user": "docs/", "internal": "tech-docs"}
    assert f"stamped {DEFINITIONS}/user.md: the definition of space 'user'" in out
    assert front(shared, f"{DEFINITIONS}/user.md")["scope"]["paths"] == ["docs/**", "README.md"]
    # Apart now, the next stamp asks nothing.
    assert WHY not in stamped(new(shared, "space", "technical"))
    assert errors(run(shared)) == []


def test_a_page_of_either_space_sets_them_apart_too(shared: AdopterRepo) -> None:
    flags = ("--space", "user", "--kind", "signpost", "--reader", "user", "--title", "Guide")
    out = stamped(new(shared, "page", "docs/guide-2.md", *flags, "--yes"))
    assert out.startswith(WHY)
    assert _internal_root(shared) == {"user": "docs/", "internal": "tech-docs"}
    assert "stamped docs/guide-2.md: a signpost page of space 'user'" in out


def test_off_a_terminal_without_yes_nothing_is_written_and_the_rerun_is_named(
    shared: AdopterRepo,
) -> None:
    before = snapshot(shared)
    message = refused(new(shared, "space", "user"))
    assert WHY in message
    assert "takes consent (COR-048 point 5), and stdin is not a terminal" in message
    assert "To consent, run: pkit living-docs new space user --yes" in message
    assert snapshot(shared) == before


@pytest.mark.parametrize(
    ("folder", "said"),
    [
        ("docs/internal", "the internal root 'docs/internal' would lie in the user root 'docs'"),
        (".", "is not a folder of the repository"),
        ("../elsewhere", "is not a folder of the repository"),
        ("/tech-docs", "is not a folder of the repository"),
    ],
)
def test_a_folder_that_is_not_beside_the_user_root_is_refused(
    shared: AdopterRepo, folder: str, said: str
) -> None:
    before = snapshot(shared)
    assert said in refused(new(shared, "space", "user", "--internal-root", folder, "--yes"))
    assert snapshot(shared) == before


def test_roots_that_are_the_repository_itself_are_refused_with_the_fix(
    shared: AdopterRepo,
) -> None:
    declare(shared, roots={"user": ".", "internal": "."}, places=[], spaces=UNDEFINED)
    message = refused(new(shared, "space", "user", "--yes"))
    assert "the user root is the repository itself" in message
    assert "`pkit config set docs.user <path>`" in message


def test_internal_root_is_refused_where_the_roots_are_apart(project: AdopterRepo) -> None:
    message = refused(new(project, "space", "api", "--internal-root", "handbook"))
    assert "only where the two documentation roots are one folder" in message


@pytest.mark.parametrize(
    ("named", "folder"), [((), "tech-docs"), (("--internal-root", "handbook/"), "handbook")]
)
def test_a_dry_run_says_it_would_set_the_root_first_and_writes_nothing(
    shared: AdopterRepo, named: tuple[str, ...], folder: str
) -> None:
    before = snapshot(shared)
    out = stamped(new(shared, "space", "user", *named, "--dry-run"))
    assert out == (
        f"dry run: nothing written. {WHY.replace('tech-docs', folder)} The stamp would run `pkit "
        f"config set docs.internal {folder}` first, under that command's consent; its checks run "
        "once the roots are apart.\n"
    )
    assert snapshot(shared) == before


def test_at_a_terminal_the_backbone_asks_and_a_decline_stamps_nothing(shared: AdopterRepo) -> None:
    # The stamp passes no `--yes` of its own: the backbone's command asks the person.
    asked = probe(shared, "asked").splitlines()
    assert asked == [WHY, "pkit config set docs.internal tech-docs", "stamped"]
    declined = probe(shared, "declined").splitlines()
    assert declined[-1] == (
        "refused: the internal root was not set apart (`pkit config set docs.internal tech-docs` "
        "exited 1), so nothing is written"
    )


#: The four capabilities a trial installed, in two orders their dependencies allow.
ORDERS = (
    ("project-management", "software-engineering", "software-analysis", "living-docs"),
    ("living-docs", "software-analysis", "project-management", "software-engineering"),
)


def _layout(repo: AdopterRepo) -> dict[str, str]:
    """The documentation layout: every file under a root, and the files that say where."""
    named = [
        CONFIG,
        LD_CONFIG,
        LOCATIONS,
        ".pkit/agents/project/overlay.yaml",
        ".pkit/capabilities/software-analysis/project/docs-locations.yaml",
    ]
    files = [p for top in ("docs", "tech-docs") for p in sorted((repo.root / top).rglob("*"))]
    return {
        rel: (repo.root / rel).read_text(encoding="utf-8")
        for rel in [*(p.relative_to(repo.root).as_posix() for p in files if p.is_file()), *named]
        if (repo.root / rel).is_file()
    }


def test_a_fresh_project_gets_one_layout_whatever_order_it_installs_in(
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    pkit_on_path: Path,
) -> None:
    """`pkit init`, the four installs in either order, then the first space: no step comes
    first, and the layouts are one (#2084)."""
    from project_kit import install

    monkeypatch.setattr(install, "provision_query_commands", lambda *_a, **_k: None)
    layouts = []
    for index, order in enumerate(ORDERS):
        repo = make_adopter_repo(root=tmp_path / f"order-{index}")
        for name in order:
            result = CliRunner().invoke(main, ["capabilities", "install", name])
            assert result.exit_code == 0, (name, result.output)
        assert (repo.root / "docs/rule-sets/analysis.md").is_file()
        out = stamped(new(repo, "space", "user", "--yes"))
        assert "recorded project rule sets = docs/rule-sets" in out
        assert "kept adr-records = docs/architecture/decisions" in out
        stamped(new(repo, "space", "technical"))
        assert errors(run(repo)) == []
        layouts.append(_layout(repo))
    assert layouts[0] == layouts[1]
    assert {
        "docs/rule-sets/analysis.md",
        f"{DEFINITIONS}/user.md",
        f"{DEFINITIONS}/technical.md",
    } <= set(layouts[0])


# --- both, filled --------------------------------------------------------------------------------


def test_a_space_and_a_page_so_created_pass_validation_once_filled(fresh: AdopterRepo) -> None:
    stamped(new(fresh, "space", "user"))
    stamped(new(fresh, "space", "technical"))
    stamped(page(fresh, "docs/start/README.md", "--title", "Start", "--path", "docs/start/*"))
    rel = fresh.root / "docs/start/README.md"
    text = rel.read_text(encoding="utf-8")
    text = text.replace(
        "<One sentence: what this folder is for, for this reader.>",
        "Where a new user starts.",
    ).replace(
        "- [<entry>](<entry>) — <what the reader finds there, in a line>.",
        "- [Guide](../guide.md) — how to use the system.",
    )
    assert not re.search(r"<[^<>]*>", text)
    rel.write_text(text, encoding="utf-8")
    assert errors(run(fresh)) == []
    assert validate_friction(fresh.root).errors == ()
    result = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "rule-sets"])
    assert result.exit_code == 0, result.output
    reach = InProcessPkit()(
        ["pkit", "rule-sets", "reach", "--json"],
        cwd=fresh.root,
        capture_output=True,
        text=True,
        check=True,
    )
    (entry,) = [
        a for a in json.loads(reach.stdout)["artefacts"] if a["path"] == "docs/start/README.md"
    ]
    rules = {rule["rule"] for rule in entry["rules"]}
    assert {"living-docs:RS-LDOC-003", "living-docs:RS-LDOC-004", "RS-USER-001"} <= rules
