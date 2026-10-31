"""Each README's list holds the numbers of the pages beside it (RS-REWORK-001).

A page or a subfolder its reader reads in order takes a number in tens, `010-`,
`020-`, and the folder's README lists them in number order (ADR-069 point 4). This
is the test `REWORK` declares as the rule's check, `page-numbering`:

- **Which READMEs:** each `README.md` that `REWORK`'s scope selects, as the
  backbone's discovery reads the scopes (`covering_rule_sets`). A check holds its
  part of a rule only where the rule binds (COR-051 point 2).
- **What is numbered:** a page `NNN-<topic>.md` or a subfolder `NNN-<topic>/`
  beside the README, its number three digits or more.
- **What holds:** each number is in tens, no two entries share one, and the README
  lists each numbered entry in number order. The README's list is its list items
  that open with a link to a numbered entry. A link elsewhere, such as in the prose
  of a section, lists nothing. A link to a subfolder names the folder or its
  `README.md`.
- **What is skipped:** a lookup page, named by its topic with no number, and a
  guide's folder, a subfolder named after its reference's folder with no number
  (ADR-069 point 1). Its parent's README lists it by name after the numbered
  entries, and this test does not check where.
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

import pytest

from project_kit.friction_discovery import covering_rule_sets, discover_artefacts

REPO = Path(__file__).resolve().parent.parent
REWORK = "tech-docs/living-docs/rule-sets/rework.md"

NUMBERED = re.compile(r"^(\d{3,})-")
LINK = re.compile(r"\[(?:[^\]\\]|\\.)*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?=\[)")


def numbered_entries(folder: Path) -> dict[str, int]:
    """The pages and subfolders beside a README that carry a number, by name."""
    entries: dict[str, int] = {}
    for child in folder.iterdir():
        found = NUMBERED.match(child.name)
        if found is None:
            continue
        if child.is_dir() or child.suffix == ".md":
            entries[child.name] = int(found.group(1))
    return entries


def listed_targets(text: str) -> list[str]:
    """The target of the link each list item opens with, in the text's order, outside
    fenced code. A list item that opens with no link, and a link anywhere else, list
    nothing."""
    targets: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        opened = FENCE.match(line)
        if opened is not None:
            marker = opened.group(1)
            if fence is None:
                fence = marker[0] * len(marker)
            elif marker.startswith(fence):
                fence = None
            continue
        if fence is None and LIST_ITEM.match(line):
            found = LINK.search(line)
            if found is not None:
                targets.append(found.group(1))
    return targets


def _entry_linked(target: str, entries: dict[str, int], folder: Path) -> str | None:
    """The numbered entry a link names, or None. A link names a page beside the README by
    its file, and a subfolder by the folder or its `README.md`."""
    if "://" in target or target.startswith(("#", "mailto:", "/")):
        return None
    path = posixpath.normpath(target.split("#", 1)[0].split("?", 1)[0])
    if path in ("", "."):
        return None
    parts = path.split("/")
    name = parts[0]
    if name not in entries:
        return None
    if len(parts) == 1:
        return name
    if (folder / name).is_dir() and parts[1:] == ["README.md"]:
        return name
    return None


def numbering_findings(readme: Path) -> list[str]:
    """What breaks RS-REWORK-001's checked part for `readme`'s folder."""
    folder = readme.parent
    entries = numbered_entries(folder)
    findings: list[str] = []
    for name, number in sorted(entries.items(), key=lambda item: (item[1], item[0])):
        if number % 10:
            findings.append(f"{name}: its number, {number}, is not in tens")
    by_number: dict[int, list[str]] = {}
    for name, number in entries.items():
        by_number.setdefault(number, []).append(name)
    for number, names in sorted(by_number.items()):
        if len(names) > 1:
            findings.append(f"{', '.join(sorted(names))}: they share the number {number}")
    listed: list[str] = []
    for target in listed_targets(readme.read_text(encoding="utf-8")):
        name = _entry_linked(target, entries, folder)
        if name is not None and name not in listed:
            listed.append(name)
    for name in sorted(set(entries) - set(listed), key=lambda n: (entries[n], n)):
        findings.append(f"{name}: the README does not list it")
    in_order = sorted(listed, key=lambda n: (entries[n], n))
    if listed != in_order:
        findings.append(
            f"the README lists {', '.join(listed)}, out of number order: {', '.join(in_order)}"
        )
    return findings


def _rework_readmes() -> list[str]:
    covering = covering_rule_sets(discover_artefacts(REPO))
    return sorted(
        location
        for location, sets in covering.items()
        if REWORK in sets and posixpath.basename(location) == "README.md"
    )


# --- the READMEs REWORK's scope selects -------------------------------------


@pytest.mark.parametrize("readme", _rework_readmes())
def test_each_readme_rework_selects_lists_its_numbered_pages_in_order(readme: str) -> None:
    findings = numbering_findings(REPO / readme)
    assert findings == [], (
        f"{readme} (RS-REWORK-001): "
        + "; ".join(findings)
        + ". Number each page or subfolder read in order in tens, and list each in the "
        "folder's README, in number order."
    )


def test_some_readme_rework_selects_has_numbered_pages() -> None:
    """The parametrised test checks a numbered folder, not only folders with none."""
    assert any(numbered_entries((REPO / readme).parent) for readme in _rework_readmes())


# --- the check itself ----------------------------------------------------------


def _folder(tmp_path: Path, readme: str, *names: str) -> Path:
    for name in names:
        target = tmp_path / name
        if name.endswith("/"):
            target.mkdir(parents=True)
            (target / "README.md").write_text("# Sub\n", encoding="utf-8")
        else:
            target.write_text("# Page\n", encoding="utf-8")
    path = tmp_path / "README.md"
    path.write_text(readme, encoding="utf-8")
    return path


def test_a_readme_listing_its_pages_in_number_order_holds(tmp_path: Path) -> None:
    readme = _folder(
        tmp_path,
        "# Guide\n\n- [Set up](010-set-up.md)\n- [Write](020-write.md#first)\n"
        "- [More](030-more/)\n",
        "010-set-up.md",
        "020-write.md",
        "030-more/",
    )
    assert numbering_findings(readme) == []


def test_a_subfolder_is_listed_by_its_readme_too(tmp_path: Path) -> None:
    readme = _folder(tmp_path, "- [More](./010-more/README.md)\n", "010-more/")
    assert numbering_findings(readme) == []


def test_a_page_listed_out_of_number_order_fails(tmp_path: Path) -> None:
    readme = _folder(tmp_path, "- [B](020-b.md)\n- [A](010-a.md)\n", "010-a.md", "020-b.md")
    assert numbering_findings(readme) == [
        "the README lists 020-b.md, 010-a.md, out of number order: 010-a.md, 020-b.md"
    ]


def test_a_numbered_page_the_readme_does_not_list_fails(tmp_path: Path) -> None:
    readme = _folder(tmp_path, "- [A](010-a.md)\n", "010-a.md", "020-b.md")
    assert numbering_findings(readme) == ["020-b.md: the README does not list it"]


def test_a_number_not_in_tens_and_a_shared_number_fail(tmp_path: Path) -> None:
    readme = _folder(
        tmp_path,
        "- [A](010-a.md)\n- [B](010-b.md)\n- [C](015-c.md)\n",
        "010-a.md",
        "010-b.md",
        "015-c.md",
    )
    assert numbering_findings(readme) == [
        "015-c.md: its number, 15, is not in tens",
        "010-a.md, 010-b.md: they share the number 10",
    ]


def test_lookup_pages_and_guide_folders_are_skipped(tmp_path: Path) -> None:
    readme = _folder(
        tmp_path,
        "- [Glossary](glossary.md)\n- [A](010-a.md)\n- [living-docs](living-docs/README.md)\n",
        "glossary.md",
        "living-docs/",
        "010-a.md",
    )
    assert numbering_findings(readme) == []


def test_a_link_in_prose_lists_nothing(tmp_path: Path) -> None:
    """A section may link a later page in its prose, and only the list is held to the
    numbers."""
    readme = _folder(
        tmp_path,
        "See [B](020-b.md) first.\n\n- **Why.** It needs [B](020-b.md#x).\n\n"
        "- [A](010-a.md)\n- [B](020-b.md)\n",
        "010-a.md",
        "020-b.md",
    )
    assert numbering_findings(readme) == []


def test_a_numbered_page_linked_only_in_prose_is_not_listed(tmp_path: Path) -> None:
    readme = _folder(tmp_path, "See [A](010-a.md).\n", "010-a.md")
    assert numbering_findings(readme) == ["010-a.md: the README does not list it"]


def test_a_link_in_fenced_code_lists_nothing(tmp_path: Path) -> None:
    readme = _folder(tmp_path, "```markdown\n- [A](010-a.md)\n```\n", "010-a.md")
    assert numbering_findings(readme) == ["010-a.md: the README does not list it"]
