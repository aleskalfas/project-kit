"""A stand-in for a browser, for the tests of `viewing_browser` (visual-communication DEC-020).

It is a real program, started as the module starts a browser, and it speaks the pipe: JSON
messages, each ended by a NUL, read on descriptor 3 and written on descriptor 4. So no test
needs a browser, and a test can have it answer, hang, die or plant a fault.

**The plan.** `stand_in` writes a program and its plan, a JSON file that says what the program
does. It holds a document for each file the module opens, by file name, as `READ` gives it, and
each span adds what only a browser could learn: `fonts`, as `CSS.getPlatformFontsForNode`
answers, `ink`, the grounds on which the span changes the picture, with `ink-when` giving
other grounds under a reader's signal set to a value, keyed `signal:value`, and `lost`, the
share of its strong ink each cause loses, by cause, `cut` or `covered`, with `lost-when` as
`ink-when`. `requests` are what the document asks for. A `fault` names a method, and the
document it strikes in, if any.

**The signals.** What `Emulation.setEmulatedMedia` set shows in every picture it takes, so a
page repaints as its signals change; under `repaints: false`, no picture shows them. The
colours a forced palette gives the planted file follow the scheme set: `colours`, by scheme,
names others.

**What the page shows of a span.** Each span the module asks it to tally holds `STRONG` device
pixels of strong ink, and loses to each cause its `lost` share of them, whatever the pictures
it was handed.

**What it leaves.** Each line of the log it writes is a JSON message, its flags and its process
first.

It runs alone, by path, so it reads only the standard library.
"""

from __future__ import annotations

import base64
import json
import os
import stat
import struct
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

READS, WRITES = 3, 4

#: How long a hang lasts: past any bound a test sets, and short of leaving a process behind.
HANG_SECONDS = 120

VERSION = "Chrome/1.2.3"

#: What a span of a face in the file answers.
HELD_FONT = {"familyName": "Held", "isCustomFont": True, "glyphCount": 4}

#: How many device pixels of strong ink each span holds, where the module tallies it.
STRONG = 10_000

#: The ground and the text colour each scheme's forced palette gives, as a browser computes them.
COLOURS = {
    "light": {"ground": "rgb(255, 255, 255)", "text": "rgb(0, 0, 0)"},
    "dark": {"ground": "rgb(0, 0, 0)", "text": "rgb(255, 255, 255)"},
}


def stand_in(folder: Path, plan: Mapping[str, Any]) -> Path:
    """Write the program in `folder`, with `plan`, and give its path."""
    folder.mkdir(parents=True, exist_ok=True)
    plan_file = folder / "plan.json"
    plan_file.write_text(json.dumps({"log": str(folder / "log.jsonl"), **plan}), encoding="utf-8")
    program = folder / "browser"
    program.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" -I "{__file__}" "{plan_file}" "$@"\n',
        encoding="utf-8",
    )
    program.chmod(program.stat().st_mode | stat.S_IXUSR)
    return program


def logged(program: Path) -> list[dict[str, Any]]:
    """What the program logged, each line a message."""
    log = program.parent / "log.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def called(program: Path, method: str) -> list[dict[str, Any]]:
    """The params of each call of `method` the program received."""
    return [each["params"] for each in logged(program) if each.get("method") == method]


def flat(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Each span of `document`, in its order."""
    return [
        span
        for page in document["pages"]
        for text in page["texts"]
        for line in text["lines"]
        for span in line
    ]


class _Browser:
    def __init__(self, plan: Mapping[str, Any]) -> None:
        self.plan = plan
        self.fault = plan.get("fault") or {}
        self.document = ""
        self.ground = ""
        self.alone: int | None = None
        self.styles: dict[str, str] = {}
        self.measured: list[int] = []
        self.held: set[str] = set()
        self.loader = 0
        self.media: dict[str, str] = {}

    def log(self, message: Mapping[str, Any]) -> None:
        with open(self.plan["log"], "a", encoding="utf-8") as log:
            log.write(json.dumps(message) + "\n")

    def send(self, message: Any) -> None:
        data = json.dumps(message).encode() + b"\0"
        while data:
            data = data[os.write(WRITES, data) :]

    def event(self, method: str, **params: Any) -> None:
        self.send({"method": method, "params": params})

    def serve(self) -> None:
        held = b""
        while True:
            data = os.read(READS, 1 << 16)
            if not data:
                return
            held += data
            while b"\0" in held:
                raw, _, held = held.partition(b"\0")
                self.answer(json.loads(raw))

    def strikes(self, method: str) -> bool:
        if self.fault.get("method") != method:
            return False
        return self.fault.get("document") in (None, self.document)

    def answer(self, message: Mapping[str, Any]) -> None:
        self.log(message)
        method, params = message["method"], message.get("params", {})
        if method == "Page.navigate":
            self.document = params["url"].rsplit("/", 1)[-1]
            self.ground, self.alone, self.styles, self.measured = "", None, {}, []
        if method == "Emulation.setEmulatedMedia":
            self.media = {each["name"]: each["value"] for each in params.get("features", [])}
        if self.strikes(method):
            self.strike(message)
            return
        if method == "Browser.close":
            if not self.plan.get("ignores_close"):
                sys.exit(0)
            return
        if method in ("Fetch.continueRequest", "Fetch.failRequest"):
            self.held.discard(params["requestId"])
            if not self.held:
                self.event("Page.lifecycleEvent", name="load", loaderId=str(self.loader))
        self.send({"id": message["id"], "result": self.result(method, params)})
        if method == "Page.navigate":
            self.navigated(params["url"])

    def strike(self, message: Mapping[str, Any]) -> None:
        kind = self.fault["kind"]
        if kind == "hang":
            # A helper of its own, which the end of its process group ends too.
            helper = subprocess.Popen(["/bin/sleep", str(HANG_SECONDS)])
            self.log({"helper": helper.pid})
            time.sleep(HANG_SECONDS)
        elif kind == "die":
            sys.stderr.write(self.fault.get("says", ""))
            sys.stderr.flush()
            os._exit(self.fault.get("exit", 1))
        elif kind == "garbage":
            os.write(WRITES, b"this is no message\0")
        elif kind == "empty":
            self.send({"id": message["id"], "result": {}})
        elif kind == "no object":
            self.send([])
        elif kind == "error of no object":
            self.send({"id": message["id"], "error": "no"})
        elif kind == "refuse":
            self.send({"id": message["id"], "error": {"code": 1, "message": "not today"}})
        elif kind == "throw":
            details = {"text": "Uncaught", "exception": {"description": "Error: no such thing"}}
            self.send({"id": message["id"], "result": {"exceptionDetails": details}})
        elif kind == "error text":
            self.send({"id": message["id"], "result": {"errorText": "net::ERR_FILE_NOT_FOUND"}})

    def result(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        if method == "Browser.getVersion":
            return {"product": self.plan.get("version", VERSION)}
        if method == "Target.createTarget":
            return {"targetId": "tab"}
        if method == "Target.attachToTarget":
            return {"sessionId": "session"}
        if method == "Page.navigate":
            self.loader += 1
            return {"frameId": "frame", "loaderId": str(self.loader)}
        if method == "Runtime.evaluate":
            return self.evaluated(params["expression"])
        if method == "DOM.getDocument":
            return {"root": {"nodeId": 1}}
        if method == "DOM.querySelectorAll":
            return {"nodeIds": [100 + index for index, _ in enumerate(self.spans())]}
        if method == "CSS.getPlatformFontsForNode":
            return {"fonts": self.spans()[params["nodeId"] - 100].get("fonts", [HELD_FONT])}
        if method == "Page.captureScreenshot":
            return {"data": base64.b64encode(self.picture(params["clip"])).decode("ascii")}
        return {}

    def spans(self) -> list[dict[str, Any]]:
        return flat(self.plan["documents"][self.document])

    def navigated(self, url: str) -> None:
        """The requests of the document, each held, then its load: the file's own request
        first. Before them, the load of what the tab showed before."""
        self.event("Page.lifecycleEvent", name="load", loaderId="what-came-before")
        requests = [url, *self.plan["documents"][self.document].get("requests", [])]
        self.held = {str(index) for index, _ in enumerate(requests)}
        for index, request in enumerate(requests):
            self.event("Fetch.requestPaused", requestId=str(index), request={"url": request})

    def evaluated(self, expression: str) -> dict[str, Any]:
        """What the module's JavaScript gives, known by its source: the plan names each. Its
        arguments follow the function, as `...[]`."""
        functions = self.plan["functions"]
        for name, source in functions.items():
            if expression.startswith(f"({source})"):
                arguments = json.loads(expression[len(source) + 2 :].strip("()."))
                return {"result": {"value": self.ran(name, arguments)}}
        raise AssertionError(f"no function of the plan: {expression[:60]}")

    def ran(self, name: str, arguments: Sequence[Any]) -> Any:
        if name == "read":
            return self.plan["documents"][self.document]["pages"]
        if name == "colours":
            scheme = self.media.get("prefers-color-scheme", "light")
            return self.plan.get("colours", COLOURS)[scheme]
        if name == "tally":
            return [self.tallied(asked["index"]) for asked in arguments[2]]
        if name == "ground":
            self.ground = arguments[1]
        elif name == "alone":
            self.alone = arguments[1] if arguments[3] else None
        elif name == "style":
            self.styles[arguments[0]] = arguments[1]
        elif name == "marked":
            self.measured = list(arguments[2])
        elif name == "unground":
            self.ground, self.alone, self.measured = "", None, []
            for each in arguments[0]:
                self.styles.pop(each, None)
        return None

    def tallied(self, index: int) -> dict[str, int]:
        """What the module's tally gives of the span of `index`: its strong ink, and how much of
        it lies past its page's edge and hidden on its page, under the signals set."""
        span = next(each for each in self.spans() if each["index"] == index)
        lost = self.when(span, "lost", {})
        return {
            "strong": STRONG,
            "past": round(lost.get("cut", 0) * STRONG),
            "hidden": round(lost.get("covered", 0) * STRONG),
        }

    def ink(self, span: Mapping[str, Any]) -> Sequence[str]:
        """The grounds on which `span` changes the picture, under the signals set."""
        return self.when(span, "ink", ())

    def when(self, span: Mapping[str, Any], field: str, otherwise: Any) -> Any:
        """The span's `field` under the signals set: as its `<field>-when` gives it under a
        signal set to a value, keyed `signal:value`, or else as it stands."""
        for held, value in span.get(f"{field}-when", {}).items():
            signal, _, wanted = held.partition(":")
            if self.media.get(signal) == wanted:
                return value
        return span.get(field, otherwise)

    def picture(self, clip: Mapping[str, float]) -> bytes:
        """A PNG's header, the size of `clip`, then what shows in it: a span alone adds to its
        band only on the grounds that show it."""
        shown = None
        if self.alone is not None:
            span = next(each for each in self.spans() if each["index"] == self.alone)
            shown = self.alone if self.ground in self.ink(span) else None
        width, height = round(clip["width"] * 2), round(clip["height"] * 2)
        header = b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", width, height)
        media = self.media if self.plan.get("repaints", True) else {}
        return header + json.dumps([self.document, self.ground, clip, shown, media]).encode()


def main() -> None:
    plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    browser = _Browser(plan)
    browser.log({"process": os.getpid(), "flags": sys.argv[2:]})
    if "says" in plan:
        sys.stderr.write(plan["says"])
        sys.stderr.flush()
    if "exit" in plan:
        sys.exit(plan["exit"])
    browser.serve()


if __name__ == "__main__":
    main()
