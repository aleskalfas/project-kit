"""Batch checkbox-mutation engine shared by check-criterion / uncheck-criterion.

Both verbs run the same DEC-038 failure-and-recovery model — validate the whole
batch up front, hard-reject on any inconsistency before mutating anything, then
apply idempotently so a half-applied batch recovers on re-run (DEC-038 D4). The
only difference between the two verbs is the target checkbox state (ticked vs.
unticked), so the engine is parameterised on that and both scripts call it.

The engine is pure: it takes the current body + the parsed targets and returns a
plan (the rewritten body plus a per-target result line), performing NO network
I/O. The calling script fetches the body, runs the engine, prints the result
lines, and — only when something actually changed — writes the new body back via
edit-issue's `gh issue edit --body-file` round-trip. Keeping the engine pure is
what lets the tests cover every D4 row offline (the issue's hard requirement).
"""

from __future__ import annotations

from dataclasses import dataclass

from _lib.criteria import Criterion, extract_criteria, set_checkbox_state


@dataclass(frozen=True)
class Target:
    """One requested checkbox mutation: a 1-based index + optional text guard."""

    index: int
    expected_text: str | None = None


@dataclass(frozen=True)
class TargetResult:
    """The outcome for one target — a single clean line, nothing to grep."""

    index: int
    ok: bool
    changed: bool
    message: str


@dataclass(frozen=True)
class BatchPlan:
    """The validated batch outcome.

    `accepted` is False when up-front validation hard-rejected the batch (a
    DEC-014 hard-reject per DEC-038 D4's first three rows); in that case
    `new_body` is None and nothing must be written. When `accepted` is True,
    `new_body` is the rewritten body (equal to the input body when every target
    was already in the requested state — the idempotent no-op path), and
    `changed` reports whether any line actually flipped.
    """

    accepted: bool
    results: tuple[TargetResult, ...]
    new_body: str | None = None
    changed: bool = False


def _guard_matches(criterion: Criterion, expected: str) -> bool:
    """The DEC-038 expected-text guard: equality on the stripped item text.

    Both sides are compared after `.strip()` on the checkbox-marker-stripped
    text. `criterion.text` is already marker-stripped and trimmed by the
    extractor (matching `show-issue --field criteria`), so the guard the caller
    copies from that command's output compares equal. Equality (not substring)
    is the rule: a substring guard would silently accept a shorter prefix of a
    longer criterion, which is exactly the reorder/mismatch case the guard
    exists to catch.
    """
    return criterion.text == expected.strip()


def plan_batch(
    body: str,
    targets: list[Target],
    *,
    target_checked: bool,
) -> BatchPlan:
    """Validate the whole batch, then build the rewritten body (DEC-038 D4).

    `target_checked` is True for check-criterion, False for uncheck-criterion.

    Validation (all up front, before any mutation):
      - index out of range            → hard-reject the whole batch;
      - index names a non-checkbox    → hard-reject (cannot tick a plain bullet);
      - expected-text guard mismatch  → hard-reject the whole batch;
      - guard text matches >1 line    → hard-reject + list the matches (DEC-038
        D4: ambiguity never silently resolves). A guard that matches several
        criteria is too loose to be the safety check it is meant to be, so it
        is refused rather than trusted to have caught a reorder.

    On any hard-reject the returned plan has `accepted=False`, `new_body=None`,
    and a result line per target explaining the refusal, so the caller reports
    and writes nothing. On acceptance the plan carries the rewritten body; a box
    already in the requested state is a no-op success (idempotent).
    """
    criteria = extract_criteria(body)
    count = len(criteria)

    # ---- validate the whole batch up front (DEC-038 D4 hard-rejects) ----
    failures: list[TargetResult] = []
    resolved: list[tuple[Target, Criterion]] = []
    for t in targets:
        if t.index < 1 or t.index > count:
            failures.append(
                TargetResult(
                    index=t.index,
                    ok=False,
                    changed=False,
                    message=(
                        f"criterion {t.index}: out of range "
                        f"(issue has {count} acceptance "
                        f"{'criterion' if count == 1 else 'criteria'})"
                    ),
                )
            )
            continue
        criterion = criteria[t.index - 1]
        if not criterion.is_checkbox:
            failures.append(
                TargetResult(
                    index=t.index,
                    ok=False,
                    changed=False,
                    message=(
                        f"criterion {t.index}: not a checkbox "
                        f"(plain bullet {criterion.text!r}); cannot tick"
                    ),
                )
            )
            continue
        if t.expected_text is not None:
            matches = [c for c in criteria if _guard_matches(c, t.expected_text)]
            if len(matches) > 1:
                where = ", ".join(str(c.index) for c in matches)
                failures.append(
                    TargetResult(
                        index=t.index,
                        ok=False,
                        changed=False,
                        message=(
                            f"criterion {t.index}: ambiguous text-guard "
                            f"{t.expected_text.strip()!r} matches "
                            f"criteria {where}; pass a unique guard or omit it"
                        ),
                    )
                )
                continue
            if not _guard_matches(criterion, t.expected_text):
                failures.append(
                    TargetResult(
                        index=t.index,
                        ok=False,
                        changed=False,
                        message=(
                            f"criterion {t.index}: text-guard mismatch — "
                            f"expected {t.expected_text.strip()!r}, "
                            f"found {criterion.text!r}; re-read and retry"
                        ),
                    )
                )
                continue
        resolved.append((t, criterion))

    if failures:
        # Validate-up-front: any hard inconsistency refuses the WHOLE batch
        # before a single mutation (DEC-038 D4). Surface a line for every
        # target so the caller sees the full picture, not just the first fault.
        all_results = list(failures)
        refused_idx = {f.index for f in failures}
        for t, _criterion in resolved:
            if t.index not in refused_idx:
                all_results.append(
                    TargetResult(
                        index=t.index,
                        ok=False,
                        changed=False,
                        message=(
                            f"criterion {t.index}: not applied "
                            "(batch refused — fix the errors above and re-run)"
                        ),
                    )
                )
        all_results.sort(key=lambda r: r.index)
        return BatchPlan(accepted=False, results=tuple(all_results))

    # ---- apply (idempotently) ----
    lines = body.splitlines(keepends=True)
    results: list[TargetResult] = []
    changed_any = False
    for t, criterion in resolved:
        if criterion.checked == target_checked:
            verb = "ticked" if target_checked else "unticked"
            results.append(
                TargetResult(
                    index=t.index,
                    ok=True,
                    changed=False,
                    message=f"criterion {t.index}: already {verb} (no-op)",
                )
            )
            continue
        lines[criterion.line_no] = set_checkbox_state(
            lines[criterion.line_no], checked=target_checked
        )
        changed_any = True
        verb = "ticked" if target_checked else "unticked"
        results.append(
            TargetResult(
                index=t.index,
                ok=True,
                changed=True,
                message=f"criterion {t.index}: {verb}",
            )
        )

    results.sort(key=lambda r: r.index)
    return BatchPlan(
        accepted=True,
        results=tuple(results),
        new_body="".join(lines),
        changed=changed_any,
    )
