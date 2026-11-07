"""`pkit visual release <library>` (visual-communication DEC-003 points 6 and 7, DEC-013,
DEC-014 point 1): a version of a library released after it is read in full and compared
with the library's previous release, every refusal before any write. Run in this process
(`tests/in_process.py`); it starts no `pkit`.

- **A project's own library,** in a project the tests build: the release it needs and the
  hash written, the version listed released, every other byte of the list kept; each
  refusal, a component no piece places among them.
- **A library the capability ships,** with `--shipped`, on a repository and a history the
  tests build where the capability is authored, the methodology's source: each refusal of
  DEC-013 point 1, in the order of its Implications; a release that writes exactly the
  released place, the record and the changeset; and a base and a library built on it
  released in one change. The capability's own checks (#2605) pass on the tree each
  release writes.

Where the capability is authored, the tree's own code runs, so the installed capability's
release is the version the tree's `package.yaml` carries (`installed_as_the_tree`).
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load, run_main
from tests.test_visual_communication_shipped_libraries import (
    BADGE,
    LABEL,
    UNFINISHED,
    add_component,
    add_library,
    built,
    built_outcome,
    comparison_outcome,
    history_outcome,
    numbers_outcome,
    released_outcome,
    set_fields,
    together_outcome,
    without_note,
)
from tests.visual_communication_project import (
    FOUNDATIONS,
    REPO,
    bound,
    copy_library,
    project,
    write,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

script, libraries, reading, shipped = load(
    "visual-communication", "release.py", "libraries", "reading", "shipped"
)

CAPABILITY_DIR = ".pkit/capabilities/visual-communication"
CHECKS = "tests/test_visual_communication_shipped_libraries.py"
OWNERSHIP = ".pkit/lifecycle/ownership.py"


@pytest.fixture(autouse=True)
def installed_as_the_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """The installed capability's release, as the `package.yaml` of the tree the command
    runs in carries it, where it carries one; the capability's own otherwise."""
    own = libraries.installed_release

    def tree() -> tuple[int, int, int]:
        package = Path.cwd() / CAPABILITY_DIR / "package.yaml"
        if not package.is_file():
            return own()
        return libraries.release_of(reading.read_yaml(package)["component"]["version"])

    monkeypatch.setattr(libraries, "installed_release", tree)


def files_under(folder: Path) -> dict[str, bytes]:
    """Every file under `folder`, relative to it, with its bytes."""
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


# --- a project's own library --------------------------------------------------------------------

LIST = "visual/libraries/libraries.yaml"

#: The list of a project that holds the foundations and its own library `parts`, written by
#: hand: a comment, flow and block mappings, and a comment on a library's line.
OWN_LIST = """\
# Our libraries.
pkit_schema: visual-communication:libraries
schema_version: 1
libraries:
  foundations:
    source: {kind: shipped}
    versions: {1.0.0: {released: false}}
  parts:  # ours
    source: {kind: project}
    versions:
      1.0.0:
        released: false
"""

#: The release the version of `parts` names before its release: one the installed
#: capability reads, older than its version.
BEFORE = "0.0.9"


def own_project(tmp: Path, listed: str = OWN_LIST) -> Path:
    """A project that holds the foundations, and version 1.0.0 of its own library `parts`,
    built on them, with a stable component, listed not released."""
    root = project(tmp)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    parts_version(root, "1.0.0", label=LABEL)
    write(root / LIST, listed)
    return root


def parts_version(root: Path, version: str, **components: Any) -> Path:
    """A version of `parts` in the library folder, built on the foundations 1, holding
    `components`, by name."""
    folder = root / "visual" / "libraries" / "parts" / version
    library = bound(
        "library",
        name="parts",
        version=version,
        kind="components",
        **{"needs-release": BEFORE, "builds-on": [{"name": "foundations", "major": 1}]},
    )
    write(folder / "library.yaml", "# Our parts.\n" + yaml_text(library))
    for name, component in components.items():
        write(folder / "components" / f"{name}.yaml", yaml_text(component))
    return folder


def list_version(root: Path, version: str) -> None:
    """`version` of `parts` listed not released, last under its `versions`."""
    path = root / LIST
    path.write_text(
        path.read_text(encoding="utf-8") + f"      {version}:\n        released: false\n",
        encoding="utf-8",
    )


def own(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def installed() -> str:
    return ".".join(map(str, libraries.installed_release()))


def test_a_version_of_the_projects_own_library_is_released(tmp_path: Path) -> None:
    root = own_project(tmp_path)
    folder = root / "visual" / "libraries" / "parts" / "1.0.0"
    library_before = (folder / "library.yaml").read_text(encoding="utf-8")

    done = own(root, "parts")

    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        "checked parts@1.0.0 on foundations@1.0.0: no finding fails",
        "parts@1.0.0 is the library's first release, so it is compared with none",
        f"wrote the release it needs, {installed()}, in visual/libraries/parts/1.0.0/library.yaml",
        f"listed parts@1.0.0 released in {LIST}, with its hash",
    ]
    assert (folder / "library.yaml").read_text(encoding="utf-8") == library_before.replace(
        f"needs-release: {BEFORE}", f"needs-release: {installed()}"
    )
    held = libraries.Held(root, "visual")
    assert held.released("parts", libraries.Version(1, 0, 0))
    assert held.hash_changes("parts", libraries.Version(1, 0, 0)) == []
    assert held.findings() == []
    text = (root / LIST).read_text(encoding="utf-8")
    kept, _, _ = OWN_LIST.partition("      1.0.0:\n")
    assert text.startswith(kept + "      1.0.0:\n        released: true\n        hash:\n")


def test_the_hash_covers_the_release_the_version_needs(tmp_path: Path) -> None:
    root = own_project(tmp_path)
    assert own(root, "parts").returncode == 0
    path = root / "visual" / "libraries" / "parts" / "1.0.0" / "library.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f"needs-release: {installed()}", "needs-release: 0.0.1"
        ),
        encoding="utf-8",
    )

    changes = libraries.Held(root, "visual").hash_changes("parts", libraries.Version(1, 0, 0))

    assert changes == ["`library.yaml` of parts@1.0.0 changed"]


def test_a_flow_list_takes_the_release_in_flow_every_other_byte_kept(tmp_path: Path) -> None:
    listed = OWN_LIST.replace(
        "    versions:\n      1.0.0:\n        released: false\n",
        "    versions: {1.0.0: {released: false}}  # the first\r\n",
    )
    root = own_project(tmp_path, listed)

    assert own(root, "parts").returncode == 0, "refused"

    text = (root / LIST).read_bytes().decode("utf-8")
    head, _, tail = listed.rpartition("{1.0.0: {released: false}}")
    assert text.startswith(head + "{1.0.0: {released: true, hash: {form: 1, hash: sha256, ")
    assert text.endswith("}}" + tail)
    assert libraries.Held(root, "visual").hash_changes("parts", libraries.Version(1, 0, 0)) == []


def test_a_later_version_is_compared_with_the_previous_release(tmp_path: Path) -> None:
    root = own_project(tmp_path)
    assert own(root, "parts").returncode == 0
    parts_version(root, "1.1.0", label=LABEL, badge=BADGE)
    list_version(root, "1.1.0")

    done = own(root, "parts")

    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines()[1:3] == [
        "parts 1.0.0 to 1.1.0: the number needs at least a minor",
        "  addition: `parts/badge`: is new (DEC-003 point 1)",
    ]
    assert libraries.Held(root, "visual").released("parts", libraries.Version(1, 1, 0))


def broken(component: dict[str, Any]) -> dict[str, Any]:
    """`component`, its field `note` removed, and the part that shows it."""
    fields = {**component["fields"], "properties": {"text": {"type": "string"}}}
    data = {**component, "fields": fields}
    data["parts"] = {"text": component["parts"]["text"]}
    return data


def test_a_break_of_a_stable_component_in_a_minor_is_refused_and_released_in_a_major(
    tmp_path: Path,
) -> None:
    root = own_project(tmp_path)
    assert own(root, "parts").returncode == 0
    parts_version(root, "1.1.0", label=broken(LABEL))
    list_version(root, "1.1.0")
    before = files_under(root / "visual")

    minor = own(root, "parts")

    assert minor.returncode == 1
    assert minor.stderr.splitlines() == [
        "error: parts@1.1.0 keeps the major of its previous release, parts@1.0.0, and breaks "
        "what it promises: raise its number to 2.0.0, or take each break back:",
        "parts 1.0.0 to 1.1.0: the number needs a major, and 1.1.0 keeps major 1",
        "  break: `parts/label`, field `note`: is removed (DEC-003 point 6)",
    ]
    assert files_under(root / "visual") == before

    parts = root / "visual" / "libraries" / "parts"
    shutil.move(parts / "1.1.0", parts / "2.0.0")
    set_fields(parts / "2.0.0" / "library.yaml", version="2.0.0")
    (root / LIST).write_text(
        (root / LIST).read_text(encoding="utf-8").replace("      1.1.0:", "      2.0.0:"),
        encoding="utf-8",
    )

    major = own(root, "parts")

    assert major.returncode == 0, major.stderr
    assert "parts 1.0.0 to 2.0.0: the number needs a major" in major.stdout.splitlines()


def test_a_component_no_piece_places_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    root = own_project(tmp_path)
    write(
        root / "visual" / "libraries" / "parts" / "1.0.0" / "components" / "unfinished.yaml",
        yaml_text(UNFINISHED),
    )
    before = files_under(root / "visual")

    done = own(root, "parts")

    assert done.returncode == 1
    assert done.stderr.splitlines() == [
        "error: parts@1.0.0 is not released: 1 finding that fails where it is read in full, "
        "each to mend in the version first:",
        "  visual/libraries/parts/1.0.0/components/unfinished.yaml#parts.box.width "
        "[formula-unreadable] (fails): parts/unfinished: "
        "the formula `=:width +` ends too early",
    ]
    assert files_under(root / "visual") == before


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ("released", "parts@1.0.0, the newest version the library folder holds, is released"),
        ("shipped", "`foundations` is a library the capability ships, which the project does not"),
        ("repository", f"{LIST} names `parts` from the source `repository`"),
        ("unlisted", f"{LIST} does not list parts@1.1.0"),
        ("unnamed", f"{LIST} names no library `tools`"),
    ],
)
def test_what_the_project_does_not_own_or_has_released_is_refused(
    tmp_path: Path, change: str, said: str
) -> None:
    root = own_project(tmp_path)
    name = {"shipped": "foundations", "unnamed": "tools"}.get(change, "parts")
    if change == "released":
        assert own(root, "parts").returncode == 0
    elif change == "repository":
        (root / LIST).write_text(
            OWN_LIST.replace(
                "source: {kind: project}",
                "source: {kind: repository, url: 'https://example.com/parts.git', ref: v1}",
            ),
            encoding="utf-8",
        )
    elif change == "unlisted":
        parts_version(root, "1.1.0", label=LABEL)
    before = files_under(root / "visual")

    done = own(root, name)

    assert done.returncode == 1
    assert done.stderr.startswith(f"error: {said}")
    assert files_under(root / "visual") == before


def test_a_write_that_fails_leaves_every_file_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = own_project(tmp_path)
    before = files_under(root / "visual")
    failing(monkeypatch, write={"libraries.yaml"})

    done = own(root, "parts")

    assert done.returncode == 1
    assert done.stderr == f"error: {LIST} could not be written: {FULL}\n"
    assert files_under(root / "visual") == before


# --- a library the capability ships -------------------------------------------------------------

PACKAGE = """\
schema_version: 1
component:
  kind: capability
  name: visual-communication
  version: {version}
"""

#: The manifest of a project that installed the capability from the methodology.
MANIFEST = """\
components:
  - kind: capability
    name: visual-communication
    origin: kit-shipped
"""


class Repository:
    """A repository the tests build, whose capability's folder ships the foundations: where
    the capability is authored, the methodology's source, unless `source` is false, where
    the capability is installed as a copy. A commit at a time, never signed. The clone's
    local folder is ignored, as the capability's `runtime_ignore` asks."""

    def __init__(self, tmp: Path, *, source: bool = True) -> None:
        self.root = tmp / "repository"
        self.folder = self.root / CAPABILITY_DIR
        shutil.copytree(FOUNDATIONS, built(self.folder))
        set_fields(built(self.folder) / "library.yaml", **{"needs-release": BEFORE})
        write(self.folder / "package.yaml", PACKAGE.format(version="0.1.0"))
        write(self.root / OWNERSHIP, (REPO / OWNERSHIP).read_text(encoding="utf-8"))
        ignored = "capabilities/visual-communication/project/local/\n"
        write(self.root / ".pkit" / ".gitignore", ignored)
        write(self.root / "CHANGELOG.md", "# Changelog\n")
        if source:
            write(self.root / "src" / "project_kit" / "__init__.py", "")
        else:
            write(self.root / ".pkit" / "manifest.yaml", MANIFEST)
        self.git("init", "-q", "-b", "main")
        self.commit("the capability")

    @property
    def built(self) -> str:
        return built(self.folder).relative_to(self.root).as_posix()

    def git(self, *args: str) -> str:
        done = subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=Tests",
                "-c",
                "user.email=tests@example.com",
                *args,
            ],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
        return done.stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--no-verify", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def release_step(self, version: str = "0.1.0", *, checks: bool = True) -> str:
        """The release step's change that writes `version` of the capability, the tree then
        holding the capability's own checks, unless `checks` is false."""
        write(self.folder / "package.yaml", PACKAGE.format(version=version))
        changelog = self.root / "CHANGELOG.md"
        entry = f"- **visual-communication {version}** — A release.\n"
        changelog.write_text(changelog.read_text(encoding="utf-8") + entry, encoding="utf-8")
        if checks:
            write(self.root / CHECKS, '"""The capability\'s own checks."""\n')
        return self.commit(f"chore(release): visual-communication {version}")

    def change(self, about: str = "A change.") -> str:
        """A change to the foundations' version being built."""
        set_fields(built(self.folder) / "components" / "figure.yaml", about=about)
        return self.commit(f"a change: {about}")

    def run(self, *args: str, root: Path | None = None) -> subprocess.CompletedProcess[str]:
        return run_main(script, *args, "--shipped", cwd=root or self.root)

    def written(self) -> list[str]:
        """Each file the working tree adds or changes since HEAD."""
        status = self.git("status", "--porcelain", "--untracked-files=all")
        return sorted(line[3:] for line in status.splitlines())

    def place(self, name: str = "foundations", version: str = "1.0.0") -> Path:
        return self.folder / "releases" / name / version


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[Repository]:
    yield Repository(tmp_path)


def refused(done: subprocess.CompletedProcess[str], repository: Repository) -> str:
    """What a refused run said, once it is shown to have written nothing."""
    assert done.returncode == 1, done.stdout
    assert repository.written() == []
    assert done.stderr.startswith("error: ")
    return done.stderr[len("error: ") :].rstrip("\n")


def test_a_first_release_writes_exactly_the_released_place_the_record_and_the_changeset(
    repository: Repository, tmp_path: Path
) -> None:
    step = repository.release_step()

    done = repository.run("foundations")

    assert done.returncode == 0, done.stderr
    [changeset] = [path for path in repository.written() if path.startswith(".changes/")]
    place = f"{CAPABILITY_DIR}/releases/foundations/1.0.0"
    assert done.stdout.splitlines() == [
        "checked foundations@1.0.0: no finding fails",
        "foundations@1.0.0 is the library's first release, so it is compared with none",
        f"released foundations@1.0.0, 4 files, to {place}/, needing release 0.1.0",
        f"recorded its hash in {CAPABILITY_DIR}/releases/foundations/releases.yaml",
        f"wrote {changeset}, a patch of visual-communication: raise its kind where the "
        f"release needs more",
    ]
    being_built = files_under(built(repository.folder))
    assert repository.written() == sorted(
        [changeset, f"{CAPABILITY_DIR}/releases/foundations/releases.yaml"]
        + [f"{place}/{rel}" for rel in being_built]
    )
    released = files_under(repository.place())
    library = being_built.pop("library.yaml").decode("utf-8")
    assert released.pop("library.yaml").decode("utf-8") == library.replace(
        f"needs-release: {BEFORE}", "needs-release: 0.1.0"
    )
    assert released == being_built
    [shipped_library] = shipped.read(repository.folder)
    [version] = shipped_library.released
    assert version.hash_changes() == []
    assert reading.read_yaml(repository.root / changeset) == {
        "component": "visual-communication",
        "kind": "patch",
        "custom": {"category": "Added"},
        "body": "`foundations` 1.0.0, a library the capability ships, is released: its files "
        "are fixed from now on, and the capability records their hash.\n",
    }
    assert shipped.release_change(repository.root, "0.1.0") == step
    the_checks_pass(tmp_path, repository)


def the_checks_pass(tmp: Path, repository: Repository) -> None:
    """The capability's own checks of the versions it ships (#2605) pass on the tree."""
    folder = repository.folder
    for index, outcome in enumerate(
        (
            released_outcome(tmp / "released", folder),
            history_outcome(repository.root, folder),
            together_outcome(tmp / "together", folder),
            built_outcome(tmp / "built", folder),
            numbers_outcome(folder),
            comparison_outcome(tmp / "compared", folder),
        )
    ):
        assert outcome.failures == [], f"check {index + 1}"


def test_a_synced_copy_is_refused(tmp_path: Path) -> None:
    repository = Repository(tmp_path, source=False)
    repository.release_step()

    said = refused(repository.run("foundations"), repository)

    assert said.startswith(
        f"{CAPABILITY_DIR} arrives in this repository as a synced copy, so no library it ships "
        f"is released here"
    )


def test_a_capability_version_no_release_wrote_is_refused(repository: Repository) -> None:
    said = refused(repository.run("foundations"), repository)

    assert said.startswith(
        "foundations@1.0.0 is not released: the history records no release of "
        "visual-communication 0.1.0"
    )


def test_a_history_not_at_hand_is_refused(repository: Repository, tmp_path: Path) -> None:
    repository.release_step()
    clone = tmp_path / "shallow"
    source = repository.root.as_uri()
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", source, str(clone)], check=True, capture_output=True
    )

    done = repository.run("foundations", root=clone)

    assert done.returncode == 1
    assert done.stderr == (
        "error: foundations@1.0.0 is not released: the clone is shallow, so the history is not "
        "at hand: fetch it whole, as a checkout with `fetch-depth: 0` does\n"
    )


def test_a_release_step_change_without_the_checks_is_refused(repository: Repository) -> None:
    step = repository.release_step(checks=False)

    said = refused(repository.run("foundations"), repository)

    assert said == (
        f"foundations@1.0.0 is not released: the tree at the release step's change that wrote "
        f"visual-communication 0.1.0, {step[:12]}, holds no {CHECKS}, so no check read the "
        f"version as that release carried it: release it after the next release that moves "
        f"the capability's version"
    )


def test_a_change_after_the_release_step_is_refused(repository: Repository) -> None:
    step = repository.release_step()
    change = repository.change()

    said = refused(repository.run("foundations"), repository)

    assert said == (
        f"1 change touched {repository.built} after the release step's change that wrote "
        f"visual-communication 0.1.0, {step[:12]}, so no release carried the version as it "
        f"stands ({change[:12]}): wait for the next release that moves the capability's "
        f"version, and release it then"
    )


def test_a_change_taken_back_on_one_side_of_a_merge_is_refused(repository: Repository) -> None:
    repository.release_step()
    repository.git("checkout", "-q", "-b", "side")
    changed = [repository.change()]
    repository.git("revert", "--no-edit", "HEAD")
    changed.append(repository.git("rev-parse", "HEAD"))
    repository.git("checkout", "-q", "main")
    write(repository.root / "elsewhere.txt", "elsewhere")
    repository.commit("elsewhere")
    repository.git("merge", "-q", "--no-ff", "--no-edit", "side")

    said = refused(repository.run("foundations"), repository)

    assert said.startswith(f"2 changes touched {repository.built} after the release step's change")
    assert all(change[:12] in said for change in changed)


def test_a_change_the_working_tree_holds_is_refused(repository: Repository) -> None:
    repository.release_step()
    write(built(repository.folder) / "components" / "new.yaml", yaml_text(BADGE))

    done = repository.run("foundations")

    assert done.returncode == 1
    assert done.stderr.startswith(
        f"error: the working tree changes {repository.built} since HEAD "
        f"({repository.built}/components/new.yaml), and the release takes the version as HEAD "
        f"holds it"
    )
    assert repository.written() == [f"{repository.built}/components/new.yaml"]


def test_a_number_already_released_is_refused(repository: Repository) -> None:
    repository.release_step()
    assert repository.run("foundations").returncode == 0
    repository.commit("release foundations 1.0.0")

    said = refused(repository.run("foundations"), repository)

    assert said == (
        "foundations@1.0.0 is released already, and a released number never names other files: "
        "raise the number in its library.yaml first"
    )


def test_a_number_below_one_carried_at_an_earlier_release_is_refused(
    repository: Repository,
) -> None:
    set_fields(built(repository.folder) / "library.yaml", version="1.1.0")
    repository.commit("foundations 1.1.0")
    step = repository.release_step("0.1.0")
    set_fields(built(repository.folder) / "library.yaml", version="1.0.1")
    repository.commit("foundations 1.0.1")
    repository.release_step("0.1.1")

    said = refused(repository.run("foundations"), repository)

    assert said == (
        f"foundations@1.0.1 is below 1.1.0, which the version being built carried at the "
        f"release {step[:12]}, and a project's copy may carry: raise its number to 1.1.0 or "
        f"above first"
    )


def test_a_base_and_a_library_built_on_it_are_released_in_one_change(
    repository: Repository, tmp_path: Path
) -> None:
    """Before the base is released, the library is refused; once it is, uncommitted, the
    library is checked on that release."""
    add_library(repository.folder, "parts", {"foundations": 1}, "1.0.0")
    add_component(repository.folder, LABEL, "label", "parts")
    repository.release_step()

    first = refused(repository.run("parts"), repository)
    base = repository.run("foundations")
    library = repository.run("parts")

    assert first == (
        "parts@1.0.0 builds on `foundations` 1, of which no version is released: release "
        "`foundations` first"
    )
    assert base.returncode == 0, base.stderr
    assert library.returncode == 0, library.stderr
    assert library.stdout.splitlines()[:2] == [
        "checked parts@1.0.0 on foundations@1.0.0: no finding fails",
        "parts@1.0.0 is the library's first release, so it is compared with none",
    ]
    assert len([path for path in repository.written() if path.startswith(".changes/")]) == 2
    the_checks_pass(tmp_path, repository)


def test_a_finding_on_the_released_bases_is_refused(repository: Repository) -> None:
    """The library reads a role the foundations' version being built declares, and their
    released version does not."""
    repository.release_step()
    assert repository.run("foundations").returncode == 0
    repository.commit("release foundations 1.0.0")
    roles = built(repository.folder) / "roles.yaml"
    data = reading.read_yaml(roles)
    data["roles"]["space.9"] = {"type": "dimension", "default": "{space.4}"}
    write(roles, yaml_text(data))
    set_fields(built(repository.folder) / "library.yaml", version="1.1.0")
    add_library(repository.folder, "parts", {"foundations": 1}, "1.0.0")
    wide = bound(
        "component",
        status="experimental",
        about="A box as wide as the widest space.",
        parts={"box": {"box": {"fill": "background"}, "width": "=@space.9", "height": "=:height"}},
    )
    add_component(repository.folder, wide, "wide", "parts")
    repository.commit("foundations 1.1.0, and parts")
    repository.release_step("0.1.1")

    said = refused(repository.run("parts"), repository)

    assert said.splitlines() == [
        "parts@1.0.0 is not released: 1 finding that fails where it is read in full, each to "
        "mend in the version first:",
        f"  {CAPABILITY_DIR}/libraries/parts/components/wide.yaml#@space.9 [unknown-role] "
        "(fails): parts/wide: a formula reading `@space.9` names a role the brand gives no "
        "value",
    ]


def test_a_break_in_a_minor_is_refused(repository: Repository) -> None:
    add_component(repository.folder, LABEL, "label", "foundations")
    repository.commit("a stable label")
    repository.release_step()
    assert repository.run("foundations").returncode == 0
    repository.commit("release foundations 1.0.0")
    without_note(repository.folder)
    set_fields(built(repository.folder) / "library.yaml", version="1.1.0")
    repository.commit("foundations 1.1.0, the label's note removed")
    repository.release_step("0.1.1")

    said = refused(repository.run("foundations"), repository)

    assert said.splitlines() == [
        "foundations@1.1.0 keeps the major of its previous release, foundations@1.0.0, and "
        "breaks what it promises: raise its number to 2.0.0, or take each break back:",
        "foundations 1.0.0 to 1.1.0: the number needs a major, and 1.1.0 keeps major 1",
        "  break: `foundations/label`, field `note`: is removed (DEC-003 point 6)",
    ]


def test_a_library_the_capability_does_not_ship_is_refused(repository: Repository) -> None:
    repository.release_step()

    said = refused(repository.run("starter"), repository)

    assert said == "the capability ships no library `starter`; it ships `foundations`"
