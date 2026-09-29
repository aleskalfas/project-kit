"""The backbone manifest for the tests of the adapter's deploy primitives.

Shared by the tests of `deploy-skills.sh` and `undeploy-capability.sh`: skills
deploy only for the capabilities the manifest registers, so a test that wants a
capability's skills deployed registers the capability first.
"""

from __future__ import annotations

from pathlib import Path


def register_capabilities(root: Path, *capabilities: str) -> None:
    """Write the backbone manifest registering exactly `capabilities`, as the
    lifecycle writes it — an adapter entry first, so the parser meets other kinds."""
    lines = [
        "schema_version: 1",
        "backbone_version: 0.0.0",
        "components:",
        "  - kind: adapter",
        "    name: claude-code",
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml",
    ]
    for cap in capabilities:
        lines += [
            "  - kind: capability",
            f"    name: {cap}",
            f"    manifest: .pkit/capabilities/{cap}/manifest.yaml",
        ]
    (root / ".pkit" / "manifest.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
