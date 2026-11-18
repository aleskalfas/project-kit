# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml==0.19.1"]
# ///
"""Run the plan's own analyse.py over the calibration's reports in two readings (project-kit#3230).

Usage:

    uv run --script readings.py <analyse.py> <reference.json> <judge-key.json> <keys-dir> \
<reports-dir> <out-dir>

analyse.py stops on the first report whose YAML document does not parse. This script runs
analyse.py's own code unchanged, imported as a module, and replaces only how a document is read:

- strict:    a document that does not parse is read as an empty document: the review grades no
             rule, so by analyse.py's own rule it gives no verdict. This is the run as its reports
             stand. Written to <out-dir>/readings-strict.md.
- recovered: in a document that does not parse, each line `evidence: <text>` on which the parser
             stops is read with its text as one single-quoted scalar, and the parse is tried again.
             Only the key `evidence` is touched, and only a value on one line; anything else stops
             the script. No report file is changed. Written to <out-dir>/readings-recovered.md.

Each line the recovered reading quoted is listed in <out-dir>/recovery.json, with its report, its
line in the YAML document and the text before and after.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError

FENCE = re.compile(r"```ya?ml\n(.*?)```", re.S)  # analyse.py's own extraction


def yaml_text(path: Path) -> str:
    text = path.read_text()
    if path.suffix == ".md":
        m = FENCE.search(text)
        if not m:
            sys.exit(f"error: {path} holds no fenced YAML document")
        text = m.group(1)
    return text


def recover(path: Path, log: list) -> dict:
    lines = yaml_text(path).split("\n")
    for _ in range(50):
        try:
            return YAML(typ="safe").load("\n".join(lines))
        except MarkedYAMLError as e:
            n = e.problem_mark.line
            line = lines[n]
            m = re.match(r"^(\s*)evidence: (.+)$", line)
            if not m or m.group(2).startswith((">", "|", "'")):
                sys.exit(f"error: {path} line {n + 1} is not a one-line evidence value: {line!r}")
            indent = len(m.group(1))
            nxt = lines[n + 1] if n + 1 < len(lines) else ""
            if (
                nxt.strip()
                and len(nxt) - len(nxt.lstrip()) > indent
                and not nxt.lstrip().startswith("- ")
            ):
                sys.exit(f"error: {path} line {n + 1}'s value runs on to the next line")
            value = m.group(2).rstrip()
            fixed = m.group(1) + "evidence: '" + value.replace("'", "''") + "'"
            log.append(
                {
                    "report": str(path),
                    "line": n + 1,
                    "error": e.problem,
                    "was": line,
                    "read-as": fixed,
                }
            )
            lines[n] = fixed
    sys.exit(f"error: {path} does not parse after 50 recoveries")


def main() -> None:
    if len(sys.argv) != 7:
        sys.exit(__doc__)
    analyse_path, ref, jkey, keys, reports, out = sys.argv[1:7]
    out = Path(out)
    spec = importlib.util.spec_from_file_location("analyse", analyse_path)
    analyse = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyse)
    original = analyse.load_doc

    unread: list[str] = []

    def strict(path: Path) -> dict:
        try:
            return original(path)
        except MarkedYAMLError:
            unread.append(str(path))
            return {}

    log: list = []

    def recovered(path: Path) -> dict:
        try:
            return original(path)
        except MarkedYAMLError:
            return recover(path, log)

    for name, loader in (("strict", strict), ("recovered", recovered)):
        analyse.load_doc = loader
        sys.argv = ["analyse.py", ref, jkey, keys, reports, str(out / f"readings-{name}.md")]
        print(f"===== {name} =====")
        analyse.main()

    (out / "recovery.json").write_text(
        json.dumps({"unparsed-reports": sorted(set(unread)), "lines-read-as-quoted": log}, indent=2)
        + "\n"
    )


if __name__ == "__main__":
    main()
