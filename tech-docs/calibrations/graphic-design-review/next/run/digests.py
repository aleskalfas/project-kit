# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema==4.26.0", "referencing==0.37.0", "ruamel.yaml==0.19.1"]
# ///
"""Print the digests the hold is compared on, for the bar `reference.json` fixes, at this
checkout (project-kit#3397).

Usage, from the repository's root:

    uv run --script digests.py <reference.json> [<effort>]

The model is the one `reference.json` pins, by its name. Its effort is the one the dispatcher
runs the reviews at, given here as the dispatcher's record gives it, and left out where the
harness names none. The capability's own code computes every digest (visual-communication
DEC-042 point 9, DEC-065 points 1 and 2).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".pkit/capabilities/visual-communication/scripts"))

from _lib import bar, calibration  # noqa: E402


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    ref = json.loads(Path(sys.argv[1]).read_text())
    majors = ref["bar"]["majors"]
    covers = [f"{rule}@{majors[rule.split('-')[1]]}" for rule in ref["bar"]["covers"]]
    data = {"bar": {"covers": covers, "at-least": ref["bar"]["at-least"]}}
    problems = [str(each) for each in bar.findings(ROOT, data)]
    if problems:
        sys.exit("error: the bar does not stand: " + "; ".join(problems))
    model = {"name": ref["model"], **({"effort": sys.argv[2]} if len(sys.argv) == 3 else {})}
    reading = calibration.read(ROOT, bar.covered(ROOT, data), model)
    print(json.dumps({"bar": data["bar"], **reading.as_data()}, indent=1))
    if reading.others:
        print("other definitions:", reading.others)


if __name__ == "__main__":
    main()
