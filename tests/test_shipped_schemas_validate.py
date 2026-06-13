"""Dogfood gate: the kit's own shipped capability schemas must pass the kit's
own validator.

The schemas-validate *engine* is unit-tested against synthetic fixtures in
`test_schemas_validate.py`. That proves the engine works — but it never points
the engine at the kit's own shipped `.pkit/capabilities/*/schemas/`. This test
closes that gap: it runs the real validator over the real shipped schemas, so
data↔companion drift in a shipped capability fails here (and in CI) instead of
escaping to an adopter. Mirrors the COR-014 self-hosting principle — the kit is
its own first adopter, so it must pass its own tools.
"""
from __future__ import annotations

from pathlib import Path

from project_kit import schemas_validate

REPO = Path(__file__).resolve().parents[1]


def test_shipped_capability_schemas_validate_clean() -> None:
    """Every shipped capability schema validates against its companion + refs."""
    report = schemas_validate.validate_all(REPO)
    if not report.is_clean:
        detail = "\n".join(
            f"  {getattr(i, 'location', '?')} → {getattr(i, 'message', i)}"
            for i in report.issues
        )
        raise AssertionError(
            "shipped capability schemas fail `pkit schemas validate`:\n" + detail
        )
