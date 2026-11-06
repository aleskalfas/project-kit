"""A builder's tool that draws a page of an HTML file in a real browser,
`scripts/browser_look.py` (#2736; PRJ-012 point 2).

No test here needs a browser or Playwright. A stand-in takes Playwright's place, which holds
what the script asks of a browser, not what a browser draws. That is the pull request's real
run, since nothing compares the image (visual-communication DEC-015 point 6).

- **The arguments:** a file, a size and a folder, with a selector, attributes, a colour scheme
  and a browser beside them. A size or an attribute that does not read ends the run at 2.
- **The stops:** no browser found, the browser dead or silent, a selector that names no one
  element, and a size the page cannot take. Each says which, and writes no image.
- **One page of several:** the browser opens to measure and again to draw, at the scale that
  gives the page's long edge the size named. It moves the page to the document's corner, and
  cuts the image to the size named, not to the page's fractional height.
- **No selector:** the window, at a device scale of 1.
- **What it sets from outside:** a style, each attribute and the colour scheme, before it draws.
- **The network:** only the file itself, `data:` and `blob:` go through, and each other request
  is named once.
- **Where it lies:** outside every tree a project receives, and Playwright reaches no lock.
"""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import tomllib
import types
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from scripts import browser_look as bl

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "browser_look.py"
SELECTOR = "section.page[data-number='2'] svg"


class Error(Exception):
    """Playwright's own error, as the stand-in raises it."""


class Silent(Error):
    """Playwright's timeout, as the stand-in raises it."""


def _png(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


@dataclass
class Browser:
    """What the stand-in holds of a page, and each thing it was asked, in order."""

    box: dict[str, Any] = field(
        default_factory=lambda: {"count": 1, "x": 60.0, "y": 768.0, "width": 1280, "height": 720}
    )
    faces: list[dict[str, str]] = field(
        default_factory=lambda: [
            {"family": "Sans", "weight": "400", "style": "normal", "status": "loaded"},
            {"family": "Gone", "weight": "400", "style": "normal", "status": "error"},
        ]
    )
    dies_at: str | None = None
    fails_with: type[Error] = Error
    asked: list[tuple[str, Any]] = field(default_factory=list[tuple[str, Any]])
    launches: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    profiles: list[Path] = field(default_factory=list[Path])

    def ask(self, step: str, what: Any = None) -> None:
        self.asked.append((step, what))
        if step == self.dies_at:
            raise self.fails_with("Target page, context or browser has been closed\nCall log:")

    def steps(self) -> list[str]:
        return [step for step, _ in self.asked]

    def what(self, step: str) -> list[Any]:
        return [what for asked, what in self.asked if asked == step]

    # What the script calls on Playwright's objects.

    def __enter__(self) -> Browser:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    @property
    def chromium(self) -> Browser:
        return self

    @property
    def pages(self) -> list[Browser]:
        return [self]

    def launch_persistent_context(self, profile: str, **options: Any) -> Browser:
        self.profiles.append(Path(profile))
        self.launches.append(options)
        self.ask("launch")
        return self

    def set_default_timeout(self, _: int) -> None:
        return None

    def route(self, *_: object) -> None:
        self.ask("route")

    def route_web_socket(self, *_: object) -> None:
        self.ask("route sockets")

    def goto(self, url: str, **_: object) -> None:
        self.ask("goto", url)

    def evaluate(self, script: str, argument: Any = None) -> Any:
        if script == bl._MEASURE:
            return self.box
        if script == bl._SET_ATTRIBUTES:
            return self.ask("attributes", argument)
        if script == bl._LOAD_FACES:
            self.ask("fonts")
            return self.faces
        raise AssertionError(script)

    def add_style_tag(self, content: str) -> None:
        self.ask("style", content)

    def screenshot(self, **options: Any) -> bytes:
        self.ask("draw", options)
        clip = options.get("clip")
        if clip is None:
            size = self.launches[-1]["viewport"]
            return _png(size["width"], size["height"])
        scale = self.launches[-1]["device_scale_factor"]
        return _png(round(clip["width"] * scale), round(clip["height"] * scale))

    def close(self) -> None:
        self.ask("close")


@pytest.fixture
def browser(monkeypatch: pytest.MonkeyPatch) -> Iterator[Browser]:
    """A stand-in for Playwright and the browser behind it, and a program it takes for Chrome."""
    stand_in = Browser()
    api = types.ModuleType("playwright.sync_api")
    api.__dict__.update(Error=Error, TimeoutError=Silent, sync_playwright=lambda: stand_in)
    package = types.ModuleType("playwright")
    package.__dict__.update(sync_api=api)
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", api)
    monkeypatch.setattr(bl, "MAC_CHROME", sys.executable)
    yield stand_in


@pytest.fixture
def document(tmp_path: Path) -> Path:
    file = tmp_path / "deck.html"
    file.write_text("<!doctype html><title>deck</title>", encoding="utf-8")
    return file


def _run(document: Path, *arguments: str, size: str = "1568x882") -> int:
    folder = document.parent / "out"
    return bl.main([str(document), "--size", size, "--folder", str(folder), *arguments])


def _images(document: Path) -> list[str]:
    return sorted(path.name for path in (document.parent / "out").glob("*"))


# The arguments.


def test_it_reads_a_file_a_size_and_a_folder_with_all_else_left_out() -> None:
    arguments = bl.parser().parse_args(["deck.html", "--size", "1568x882", "--folder", "out"])

    assert arguments.file == Path("deck.html")
    assert arguments.size == bl.Size(1568, 882)
    assert arguments.folder == Path("out")
    assert arguments.selector is None
    assert arguments.attribute == []
    assert arguments.colour_scheme is None
    assert arguments.browser is None


def test_it_reads_a_selector_attributes_a_colour_scheme_and_a_browser() -> None:
    arguments = bl.parser().parse_args(
        [
            "deck.html",
            "--size",
            "1568x882",
            "--folder",
            "out",
            "--selector",
            SELECTOR,
            "--attribute",
            "data-mode=dark",
            "--attribute",
            "data-empty=",
            "--colour-scheme",
            "dark",
            "--browser",
            "/opt/chrome",
        ]
    )

    assert arguments.selector == SELECTOR
    assert arguments.attribute == [("data-mode", "dark"), ("data-empty", "")]
    assert arguments.colour_scheme == "dark"
    assert arguments.browser == Path("/opt/chrome")


@pytest.mark.parametrize(
    "arguments",
    [
        ["deck.html", "--folder", "out"],
        ["deck.html", "--size", "1568x882"],
        ["deck.html", "--size", "1568", "--folder", "out"],
        ["deck.html", "--size", "0x882", "--folder", "out"],
        ["deck.html", "--size", "1568x882.5", "--folder", "out"],
        ["deck.html", "--size", "1568x882", "--folder", "out", "--attribute", "dark"],
        ["deck.html", "--size", "1568x882", "--folder", "out", "--attribute", "=dark"],
        ["deck.html", "--size", "1568x882", "--folder", "out", "--colour-scheme", "blue"],
    ],
)
def test_arguments_that_do_not_read_end_the_run_at_two(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as ended:
        bl.main(arguments)

    assert ended.value.code == 2


# The stops.


def test_no_browser_found_stops_and_says_so(
    document: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(bl, "MAC_CHROME", str(document.parent / "no-chrome"))
    monkeypatch.setattr(bl.shutil, "which", lambda _: None)

    assert _run(document) == 1

    stopped = capsys.readouterr().err
    assert stopped.startswith("stopped: no browser found")
    assert "no-chrome" in stopped and "google-chrome" in stopped and "--browser" in stopped
    assert not (document.parent / "out").exists()


def test_a_browser_named_that_is_no_program_stops(
    document: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    named = document.parent / "chrome"

    assert _run(document, "--browser", str(named)) == 1

    assert capsys.readouterr().err == f"stopped: no browser found: {named} is no program\n"


def test_chrome_on_the_path_is_found_where_none_lies_in_the_mac_place(
    document: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bl, "MAC_CHROME", str(document.parent / "no-chrome"))
    monkeypatch.setattr(bl.shutil, "which", lambda name: f"/bin/{name}")

    assert bl.find_browser(None) == Path("/bin/google-chrome")


@pytest.mark.parametrize(
    ("dies_at", "fails_with", "says"),
    [
        ("launch", Error, "the browser died: Target page"),
        ("goto", Error, "the browser died: Target page"),
        ("draw", Error, "the browser died: Target page"),
        ("draw", Silent, "the browser did not answer: Target page"),
    ],
)
def test_a_browser_that_dies_stops_the_run_and_leaves_no_image_and_no_profile(
    browser: Browser,
    document: Path,
    capsys: pytest.CaptureFixture[str],
    dies_at: str,
    fails_with: type[Error],
    says: str,
) -> None:
    browser.dies_at = dies_at
    browser.fails_with = fails_with

    assert _run(document, "--selector", SELECTOR) == 1

    assert capsys.readouterr().err.startswith(f"stopped: {says}")
    assert _images(document) == []


@pytest.mark.parametrize(
    ("count", "says"),
    [
        (None, "the selector does not read"),
        (0, "the selector names 0 elements"),
        (2, "the selector names 2 elements"),
    ],
)
def test_a_selector_that_names_no_one_element_stops_the_run(
    browser: Browser,
    document: Path,
    capsys: pytest.CaptureFixture[str],
    count: int | None,
    says: str,
) -> None:
    browser.box = {"count": count}

    assert _run(document, "--selector", SELECTOR) == 1

    assert says in capsys.readouterr().err
    assert "draw" not in browser.steps()
    assert _images(document) == []


def test_an_element_with_no_size_stops_the_run(
    browser: Browser, document: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    browser.box = {"count": 1, "x": 0, "y": 0, "width": 0, "height": 0}

    assert _run(document, "--selector", SELECTOR) == 1

    assert "no size" in capsys.readouterr().err


@pytest.mark.parametrize("size", ["1568x1000", "1568x880", "882x1568"])
def test_a_size_that_does_not_fit_the_page_stops_the_run_rather_than_crop_it(
    browser: Browser, document: Path, capsys: pytest.CaptureFixture[str], size: str
) -> None:
    assert _run(document, "--selector", SELECTOR, size=size) == 1

    assert "the size does not fit the page" in capsys.readouterr().err
    assert "draw" not in browser.steps()
    assert _images(document) == []


def test_a_browser_that_draws_another_size_writes_no_image(
    browser: Browser,
    document: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(browser, "screenshot", lambda **_: _png(1568, 599))

    assert _run(document, "--selector", SELECTOR) == 1

    assert "the browser drew 1568x599, not 1568x882" in capsys.readouterr().err
    assert _images(document) == []


def test_no_file_stops_the_run(
    browser: Browser, document: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(document.parent / "gone.html") == 1

    assert "no such file" in capsys.readouterr().err
    assert browser.steps() == []


# One page of several.


def test_a_page_opens_to_measure_and_again_to_draw_at_the_scale_of_its_long_edge(
    browser: Browser, document: Path
) -> None:
    assert _run(document, "--selector", SELECTOR) == 0

    assert [launch["device_scale_factor"] for launch in browser.launches] == [1, 1568 / 1280]
    assert browser.steps().count("close") == 2
    assert (document.parent / "out" / "deck.png").read_bytes() == _png(1568, 882)


def test_the_page_moves_to_the_document_s_corner_wherever_the_document_puts_it(
    browser: Browser, document: Path
) -> None:
    assert _run(document, "--selector", SELECTOR) == 0

    assert (
        browser.what("style")[-1]
        == f":is({SELECTOR}) {{ translate: -60.0px -768.0px !important; }}"
    )
    (options,) = browser.what("draw")
    assert options["clip"] == {"x": 0, "y": 0, "width": 1280, "height": 720}
    assert options["full_page"] is True


def test_a_page_of_fractional_height_gives_the_size_named_and_not_the_browser_s_rounding(
    browser: Browser, document: Path
) -> None:
    browser.box = {"count": 1, "x": 60.0, "y": 24.0, "width": 1280, "height": 488.6875}

    assert _run(document, "--selector", SELECTOR, size="1568x598") == 0

    (options,) = browser.what("draw")
    assert options["clip"]["height"] == pytest.approx(598 * 1280 / 1568)
    assert (document.parent / "out" / "deck.png").read_bytes() == _png(1568, 598)


@pytest.mark.parametrize("size", ["1568x598", "1568x600"])
def test_a_fractional_page_takes_either_size_its_rounding_gives(
    browser: Browser, document: Path, size: str
) -> None:
    """The viewing step's tool gives 600: it rounds 488.69 to 489, scales it and rounds up."""
    browser.box = {"count": 1, "x": 60.0, "y": 24.0, "width": 1280, "height": 488.6875}

    assert _run(document, "--selector", SELECTOR, size=size) == 0

    width, height = size.split("x")
    assert (document.parent / "out" / "deck.png").read_bytes() == _png(int(width), int(height))


def test_the_allowance_grows_with_the_scale_as_the_step_s_rounding_does() -> None:
    assert bl.scale_of(bl.Box(0, 0, 300.4, 100.6), bl.Size(1568, 528)) == 1568 / 300.4


def test_an_upright_page_takes_its_scale_from_its_height(browser: Browser, document: Path) -> None:
    browser.box = {"count": 1, "x": 0, "y": 0, "width": 720.5, "height": 1280}

    assert _run(document, "--selector", SELECTOR, size="882x1568") == 0

    assert browser.launches[-1]["device_scale_factor"] == 1568 / 1280


def test_the_style_reaches_each_element_beside_the_page_and_those_that_hold_it() -> None:
    page = f":is({SELECTOR})"

    style = bl.outside_style(SELECTOR)

    assert f":has({page}) > :not(:has({page}), {page}) {{ opacity: 0 !important; }}" in style


def test_the_style_leaves_room_past_the_end_of_the_document() -> None:
    assert 'html::after { content: ""; display: block; height: 8px; }' in bl.outside_style("p")


# No selector.


def test_with_no_selector_it_draws_the_window_once_at_a_device_scale_of_one(
    browser: Browser, document: Path
) -> None:
    assert _run(document, size="1400x900") == 0

    assert [launch["device_scale_factor"] for launch in browser.launches] == [1]
    assert browser.launches[0]["viewport"] == {"width": 1400, "height": 900}
    assert "style" not in browser.steps()
    assert "clip" not in browser.what("draw")[0]
    assert (document.parent / "out" / "deck.png").read_bytes() == _png(1400, 900)


# What it sets from outside.


def test_the_style_the_attributes_and_the_fonts_all_come_before_it_draws(
    browser: Browser, document: Path
) -> None:
    arguments = ["--selector", SELECTOR, "--attribute", "data-mode=dark"]

    assert _run(document, *arguments) == 0

    steps = browser.steps()
    last_open = len(steps) - steps[::-1].index("goto") - 1
    assert steps[last_open:] == ["goto", "attributes", "style", "fonts", "style", "draw", "close"]
    assert browser.what("attributes")[-1] == [SELECTOR, [("data-mode", "dark")]]
    assert browser.what("style")[-2] == bl.outside_style(SELECTOR)


def test_the_colour_scheme_is_set_at_each_launch(browser: Browser, document: Path) -> None:
    assert _run(document, "--selector", SELECTOR, "--colour-scheme", "dark") == 0

    assert [launch["color_scheme"] for launch in browser.launches] == ["dark", "dark"]


def test_it_says_of_each_face_whether_it_loaded(
    browser: Browser, document: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(document) == 0

    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == "face loaded: Sans 400 normal"
    assert printed[1] == "face not loaded (error): Gone 400 normal"
    assert printed[2].startswith("image: ")


def test_it_draws_a_real_chrome_headless_on_a_profile_it_then_removes(
    browser: Browser, document: Path
) -> None:
    assert _run(document, "--selector", SELECTOR) == 0

    assert browser.launches[0]["executable_path"] == sys.executable
    assert browser.launches[0]["headless"] is True
    assert {profile.parent for profile in browser.profiles} == {document.parent / "out"}
    assert not any(profile.exists() for profile in browser.profiles)
    assert _images(document) == ["deck.png"]


def test_chrome_s_crash_database_lies_in_the_throwaway_profile(
    browser: Browser, document: Path
) -> None:
    assert _run(document, "--selector", SELECTOR) == 0

    for launch, profile in zip(browser.launches, browser.profiles, strict=True):
        assert launch["env"]["BREAKPAD_DUMP_LOCATION"] == str(profile)
        assert launch["env"]["PATH"] == os.environ["PATH"]


def test_the_file_stays_as_it_was(browser: Browser, document: Path) -> None:
    before = document.read_bytes()

    assert _run(document, "--selector", SELECTOR, "--attribute", "data-mode=dark") == 0

    assert document.read_bytes() == before


# The network.


class Route:
    """A routed request, as far as the script reads it."""

    def __init__(self, url: str) -> None:
        self.request = types.SimpleNamespace(url=url)
        self.url = url
        self.outcome: str | None = None

    def continue_(self) -> None:
        self.outcome = "went through"

    def abort(self) -> None:
        self.outcome = "refused"


OWN = "file:///work/deck.html"


@pytest.mark.parametrize(
    "url", [OWN, f"{OWN}#page-2", "data:image/png;base64,AAAA", "blob:null/1234"]
)
def test_the_file_data_and_blobs_go_through(url: str, capsys: pytest.CaptureFixture[str]) -> None:
    refuse_request, _ = bl._refuser(OWN)
    route = Route(url)

    refuse_request(route)

    assert route.outcome == "went through"
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "url", ["https://example.org/a.png", "file:///work/picture.png", "file:///etc/hosts"]
)
def test_every_other_request_is_refused_and_named(
    url: str, capsys: pytest.CaptureFixture[str]
) -> None:
    refuse_request, _ = bl._refuser(OWN)
    route = Route(url)

    refuse_request(route)

    assert route.outcome == "refused"
    assert capsys.readouterr().out == f"refused: {url}\n"


def test_a_socket_is_named_and_left_with_no_server(capsys: pytest.CaptureFixture[str]) -> None:
    _, refuse_socket = bl._refuser(OWN)

    refuse_socket(Route("wss://example.org/ws"))

    assert capsys.readouterr().out == "refused: wss://example.org/ws\n"


def test_a_request_made_again_is_named_once(capsys: pytest.CaptureFixture[str]) -> None:
    refuse_request, _ = bl._refuser(OWN)

    refuse_request(Route("https://example.org/a.png"))
    refuse_request(Route("https://example.org/a.png"))

    assert capsys.readouterr().out == "refused: https://example.org/a.png\n"


def test_both_opens_of_a_page_share_one_list_of_what_was_refused(
    browser: Browser,
    document: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def route(handler: Any) -> None:
        handler(Route("https://example.org/a.png"))

    monkeypatch.setattr(browser, "route", lambda _, handler: route(handler))

    assert _run(document, "--selector", SELECTOR) == 0

    assert capsys.readouterr().out.count("refused: https://example.org/a.png") == 1


# Where it lies, and how it runs.


def test_it_imports_with_no_playwright_and_says_so_where_it_would_draw(tmp_path: Path) -> None:
    code = (
        "import sys; sys.modules['playwright'] = None\n"
        "from pathlib import Path\n"
        "from scripts import browser_look as bl\n"
        "folder = Path(sys.argv[1])\n"
        "request = bl.Request(folder / 'd.html', folder, bl.Size(1, 1), Path(sys.executable))\n"
        "try:\n"
        "    bl.draw(request)\n"
        "except bl.Stop as stop:\n"
        "    print(stop)\n"
    )

    ran = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert ran.returncode == 0, ran.stderr
    assert ran.stdout.startswith("no Playwright here")


def test_it_runs_as_a_program_of_its_own_with_playwright_pinned_in_its_header() -> None:
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()

    assert lines[0] == "#!/usr/bin/env -S uv run --script"
    assert '#   "playwright==1.64.1",' in lines
    assert os.access(SCRIPT, os.X_OK)


def test_it_lies_outside_every_tree_a_project_receives() -> None:
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = project["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert SCRIPT.relative_to(REPO).parts[0] == "scripts"
    assert all(source.startswith(".pkit/") for source in wheel["force-include"])


@pytest.mark.parametrize("path", ["pyproject.toml", "uv.lock"])
def test_playwright_reaches_no_file_of_the_repository_s_environment(path: str) -> None:
    assert "playwright" not in (REPO / path).read_text(encoding="utf-8").lower()


def test_it_joins_no_check() -> None:
    assert "browser_look" not in (REPO / "scripts" / "check.sh").read_text(encoding="utf-8")
