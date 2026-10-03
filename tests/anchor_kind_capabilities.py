"""A fixture capability that registers anchor kinds, and resolvers for it (COR-050 point 2).

No shipped capability registers an anchor kind, so the tests that run a
resolver — the friction checks' (`test_friction_anchor_kinds`) and rule-set
validation's (`test_rule_sets`) — stand one up in an adopter repository:
`register_kinds` writes the capability's `package.yaml`, with the kinds under
`friction.kinds` and the one `commands:` leaf they name, and registers it in
the backbone manifest. The resolver bodies here are the leaf's script.
"""

from __future__ import annotations

import stat
from pathlib import Path

from project_kit.manifest import (
    ORIGIN_KIT_SHIPPED,
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)

RESOLVER = "scripts/resolve.py"

# A resolver for `source` anchors: a source `<value>` is captured at
# `sources/<value>.md`, and denotes nothing without it. It refuses to answer
# unless run as the query policy runs it — `--json`, `--` and then the anchor
# value as its arguments, the offline marker set, the base override removed,
# from the project root — and logs each value it is asked for to
# `$RESOLVER_LOG`, a file outside the project.
ASKED = """\
import json, os, sys
flag, end_of_options, value = sys.argv[1:]
offline = os.environ.get("PKIT_OFFLINE") == os.environ.get("UV_OFFLINE") == "1"
if (flag, end_of_options) != ("--json", "--") or not offline or "PKIT_CHECK_BASE" in os.environ:
    sys.exit("not run under the query policy")
if os.environ.get("RESOLVER_LOG"):
    with open(os.environ["RESOLVER_LOG"], "a") as log:
        log.write(value + "\\n")
"""
RESOLVING = (
    ASKED
    + """\
captured = f"sources/{value}.md"
print(json.dumps({"paths": [captured] if os.path.isfile(captured) else []}))
"""
)
# One that logs the value it was asked for and then hangs.
HANGING = ASKED + "import time\ntime.sleep(60)\n"


def register_kinds(
    root: Path,
    name: str,
    *,
    kinds: dict[str, str],
    contract: bool = True,
    script_body: str | None = None,
    shebang: str = "#!/usr/bin/env python3",
    origin: str = ORIGIN_KIT_SHIPPED,
) -> Path:
    """A fixture capability at `.pkit/capabilities/<name>/`, registered in the backbone
    manifest, registering each `kind -> command reference` under `friction.kinds`. Its
    one leaf, `resolve`, declares the query contract unless told not to; `script_body`
    writes the leaf's script, executable, under `shebang`. `origin` is the registry
    entry's: a test that runs a sync over the capability gives one a sync leaves alone."""
    cap_dir = root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    declaration = "    query-contract: true\n" if contract else ""
    registered = "".join(f"    {kind}:\n      command: {ref}\n" for kind, ref in kinds.items())
    (cap_dir / "package.yaml").write_text(
        f"schema_version: 2\ncomponent:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n"
        f'description: Fixture capability registering anchor kinds.\nrequires_backbone: ">=0.1.0"\n'
        f"commands:\n  resolve:\n    script: {RESOLVER}\n    help: Resolve an anchor.\n"
        f"{declaration}friction:\n  kinds:\n{registered}",
        encoding="utf-8",
    )
    if script_body is not None:
        script = cap_dir / RESOLVER
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(f"{shebang}\n{script_body}", encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=name,
            manifest=f".pkit/capabilities/{name}/manifest.yaml",
            origin=origin,
        )
    )
    write_backbone_manifest(root, backbone)
    return cap_dir
