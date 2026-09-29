#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — fill-doc-check (verb-subject per DEC-020).

The default filler of the `pkit::work-tracking:doc-check` data point (DEC-053):
the project's code-to-doc mapping (DEC-015), as the point's obligations — one
per well-formed rule of `code_path_to_doc_mapping.rules` in
`project/config.yaml`, keyed by the rule.

The backbone runs it wherever the point resolves — `pkit validate`, `pkit
status`, `pkit connections resolve` — as a query (COR-052 point 6): from the
project root, with `--json` alone and the offline marker set. It takes no
parameter, reads one file, writes nothing and needs no network. It is this
capability's own contribution to its own point, so it takes part on every
resolution, like an always-included default: a static `default` in package
metadata cannot hold the project's mapping.

It is exempt from the bootstrap gate (`_lib/bootstrap_gate.EXEMPT_VERBS`): it
reports what the config says — no config, no obligations — and the verb that
acts on the point, `check-doc-mapping`, stays gated.

Offline, `uv` resolves this script's one dependency from its cache; `pkit init`
and `pkit sync` provision it there, as they do for every query command. Until
then the filler gives no answer — its environment not provisioned — and the
point, whose inert policy is `fail`, does not resolve.

Usage:
  pkit pm fill-doc-check           one line per obligation, for a person
  pkit pm fill-doc-check --json    the filler envelope {schema_version, value}

Exit codes:
  0  answered
  1  the mapping is not a mapping (the config schema's error too): no answer
  2  the capability is not found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import doc_check  # noqa: E402
from _lib.gh import load_adopter_config  # noqa: E402
from _lib.membership import CAPABILITY_NAME, resolve_capability_root  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Print the code-to-doc mapping as the obligations of the "
            f"{doc_check.POINT} data point (DEC-053) — its default filler. "
            "Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the filler envelope {schema_version, value}, as the backbone reads it.",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    config = load_adopter_config(capability_root)
    mapping = config.get(doc_check.MAPPING_KEY)
    if mapping is not None and not isinstance(mapping, dict):
        print(
            f"error: {doc_check.MAPPING_KEY} must be a mapping with `enforce:` and "
            "`rules:` (per ADR-019); no obligations can be read from it.",
            file=sys.stderr,
        )
        return 1

    envelope = doc_check.envelope(config)
    if args.json:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
        return 0
    obligations = envelope["value"]
    print(f"{doc_check.POINT}: {len(obligations)} mapping obligation(s)")
    for obligation in obligations:
        print(f"  {obligation['id']} → {', '.join(obligation['documents'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
