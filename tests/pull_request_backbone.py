"""The backbone's pull-request noun, run in this process for project-management's tests.

pm's merge verbs ask `pkit pull-request` by subprocess (`_lib.merge_queue`).
A test routes that one seam, `merge_queue._answers`, to the backbone's CLI in
this process, so the real backbone mechanic — the reading, the wait with its
two-reading rule, the merge requests — runs against the test's fakes: a fake
`gh`, readings the test scripts, a clock the wait's sleeps advance. Nothing
spawns `pkit`.

`reading(mq, **fields)` builds pm's reading of a backbone reading with those
fields, through the backbone's own document, so a test's reading says what the
backbone would conclude from it.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import cli
from project_kit import pull_request_landing as landing

#: A fake `gh`: the command, and what it answered.
FakeGh = Callable[[Sequence[str]], Any]


def reading(mq: Any, **fields: Any) -> Any:
    """pm's `Reading` of a backbone reading with `fields` (pm's `Removal`
    accepted), as the backbone's document states it."""
    return mq.decode_reading(backbone_reading(fields).as_json())


def backbone_reading(fields: Any) -> landing.Reading:
    """The backbone's reading with `fields` — a mapping of its fields, or pm's
    `Reading` — keeping only what GitHub answers; the backbone concludes the
    rest itself."""
    if not isinstance(fields, dict):
        fields = {f.name: getattr(fields, f.name) for f in dataclasses.fields(fields)}
    raw = {f.name: fields[f.name] for f in dataclasses.fields(landing.Reading) if f.name in fields}
    removal = raw.get("removal")
    if removal is not None:
        raw["removal"] = landing.Removal(removal.at, removal.reason, removal.head_oid)
    return landing.Reading(**raw)


def in_process(
    monkeypatch: pytest.MonkeyPatch,
    mq: Any,
    *,
    gh: FakeGh | None = None,
    read: Callable[[int, dict[str, Any]], Any] | None = None,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
) -> None:
    """Route pm's backbone seam (`mq._answers`) to the backbone's CLI in this process.

    `gh` stands in for the backbone's `gh` (default: the one on PATH). `read`
    is a pm-level scripted reading — `(pr_number, config)` answering pm's
    `Reading` or raising pm's `Unreadable` — which the backbone's own readings
    (the wait's, the dequeue's) answer from too, so a test that scripts pm's
    `merge_queue.read` scripts the backbone's with the same sequence. `sleep`
    and `clock` are the wait's.
    """
    if gh is not None:
        monkeypatch.setattr(landing, "run_gh", gh)
    if read is not None:

        def backbone_read(pr_number: int, *, gh: Any = None) -> landing.Reading:
            try:
                answered = read(pr_number, {})
            except mq.Unreadable as exc:
                raise landing.Unreadable(str(exc)) from None
            return backbone_reading(answered)

        monkeypatch.setattr(landing, "read", backbone_read)
    if sleep is not None:
        monkeypatch.setattr(landing, "_sleep", sleep)
    if clock is not None:
        monkeypatch.setattr(landing, "_monotonic", clock)

    def answers(
        args: list[str], config: dict[str, Any], *, timeout_seconds: float | None = None
    ) -> Iterator[dict[str, Any]]:
        result = CliRunner().invoke(
            cli.main, ["pull-request", *args, "--json"], catch_exceptions=False
        )
        yield from (json.loads(line) for line in result.stdout.splitlines() if line.strip())

    monkeypatch.setattr(mq, "_answers", answers)
