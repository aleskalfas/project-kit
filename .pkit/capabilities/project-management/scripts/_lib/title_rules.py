"""Title rules — the one reader of ``titles.yaml``'s per-surface checks.

``titles.yaml`` declares, for every title surface (each issue type, the
milestone, the PR), a ``pattern`` and a list of ``validations``. Each validation
names the check that enforces it (``check``), the finding label a violation is
reported under (``name``) and its severity token. Callers ask this module rather
than reading ``pattern`` themselves: a reader that took only the pattern left
every other declared rule unenforced while the title validated clean (#803).

The check kinds
---------------

* ``pattern`` — the title matches the entry's ``pattern``. Run whenever the entry
  has one, so an entry with no ``validations`` keeps its regex gate; a declared
  ``pattern`` validation supplies the severity and the label.
* ``forbid`` / ``require`` — the title's *text* must not / must contain a match
  for ``regex`` (``re.search``).
* ``min-length`` / ``max-length`` — the text is at least / at most ``length``
  characters long.
* ``kind-prefix`` / ``type-alignment`` — need what the title does not carry (the
  issue's kind label; the closing issues' kinds). This module only binds them;
  validate-issue and the PR validator evaluate them and read their declared
  severity through :func:`declared_severity`.

The *text* is the pattern's named group ``text`` when it has one — an issue
title after its ``[Type]`` prefix, a PR title's summary after ``type(scope):`` —
and otherwise the whole title.

Wording rules are enforced where a title is written
---------------------------------------------------

The text checks are wording rules. Filing and retitling run them at their
declared severity. Validating an existing issue at a lifecycle transition
(``at_transition=True``) reports a blocking one as a warning, so a title written
before the rule was enforced does not wall the move in flight — the phase split
the kind-prefix rule already carries (#410, #895). The pattern check is not
split: a title the pattern does not recognise is refused everywhere.

A declared check this module cannot run — an unknown ``check``, a ``forbid``
without a ``regex``, a ``min-length`` without a ``length`` — raises
:class:`ValueError` instead of passing: a rule nothing runs is the defect this
module exists to close.

Dependency-free at import time (``re`` only), so any PEP 723 script can import
it; callers load ``titles.yaml`` themselves and pass the parsed dict in.
"""

from __future__ import annotations

import re

SEVERITY_HARD_REJECT = "hard-reject"
SEVERITY_BYPASSABLE = "bypassable-with-audit"
SEVERITY_WARNING = "warning"

#: The severities that refuse an operation (as opposed to a warning).
BLOCKING_SEVERITIES = (SEVERITY_HARD_REJECT, SEVERITY_BYPASSABLE)

CHECK_PATTERN = "pattern"
CHECK_FORBID = "forbid"
CHECK_REQUIRE = "require"
CHECK_MIN_LENGTH = "min-length"
CHECK_MAX_LENGTH = "max-length"
CHECK_KIND_PREFIX = "kind-prefix"
CHECK_TYPE_ALIGNMENT = "type-alignment"

#: Checks decided from the title alone, run by :func:`check_title`.
TEXT_CHECKS = frozenset({CHECK_FORBID, CHECK_REQUIRE, CHECK_MIN_LENGTH, CHECK_MAX_LENGTH})
#: Checks that need context the title does not carry; their callers run them.
CONTEXT_CHECKS = frozenset({CHECK_KIND_PREFIX, CHECK_TYPE_ALIGNMENT})
#: Every check kind a validation may name.
CHECKS = frozenset({CHECK_PATTERN}) | TEXT_CHECKS | CONTEXT_CHECKS

#: The label a pattern miss is reported under when no validation names it.
DEFAULT_PATTERN_LABEL = "title.pattern"

_TEXT_GROUP = "text"
_SEVERITY_TOKEN = re.compile(r"\[validation-severity:([a-z-]+)\]")

TitleFinding = tuple[str, str, str]
"""``(severity, label, detail)`` — the shape placeholder_detection returns too."""


def issue_key(structural_type: str) -> str:
    """The ``formats`` key of the entry governing an issue type's titles."""
    return f"issue-{structural_type}"


def format_entry(titles: dict, key: str) -> dict | None:
    """The ``formats[key]`` entry, or ``None`` when absent or malformed."""
    formats = titles.get("formats") if isinstance(titles, dict) else None
    entry = formats.get(key) if isinstance(formats, dict) else None
    return entry if isinstance(entry, dict) else None


def pattern_for(titles: dict, key: str) -> str | None:
    """The entry's title regex, or ``None`` (no entry, or a free-form surface)."""
    entry = format_entry(titles, key)
    pattern = entry.get("pattern") if entry is not None else None
    return pattern if isinstance(pattern, str) and pattern else None


def validations(entry: dict | None) -> list[dict]:
    """The entry's declared validations (malformed items dropped)."""
    raw = entry.get("validations") if isinstance(entry, dict) else None
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def declared_severity(entry: dict | None, check: str, default: str) -> str:
    """The severity the entry declares for ``check``, else ``default``.

    For the context checks (and the pattern), whose single validation per entry
    the caller evaluates itself.
    """
    for item in validations(entry):
        if item.get("check") == check:
            return _severity(item.get("severity"), default)
    return default


def check_title(
    titles: dict,
    key: str,
    title: str,
    *,
    at_transition: bool = False,
) -> list[TitleFinding]:
    """Run the entry's pattern and text checks against ``title``.

    Returns one ``(severity, label, detail)`` per violated check, in declaration
    order; empty when the title passes or ``titles`` has no entry for ``key``. A
    pattern miss is reported alone — the text checks need the text the pattern
    delimits. ``at_transition`` reports a blocking text check as a warning (see
    the module docstring).
    """
    entry = format_entry(titles, key)
    if entry is None:
        return []
    declared = validations(entry)
    for item in declared:
        _require_runnable(key, item)

    text = title
    pattern = pattern_for(titles, key)
    if pattern is not None:
        match = re.match(pattern, title)
        if match is None:
            return [_pattern_finding(key, declared, pattern, title)]
        text = match.groupdict().get(_TEXT_GROUP) or title

    findings: list[TitleFinding] = []
    for item in declared:
        check = item["check"]
        if check not in TEXT_CHECKS:
            continue
        specifics = _violation(check, item, text)
        if specifics is None:
            continue
        severity = _severity(item.get("severity"), SEVERITY_WARNING)
        if at_transition and severity in BLOCKING_SEVERITIES:
            severity = SEVERITY_WARNING
        findings.append((severity, _label(item), f"{_rule_text(item)} — {specifics}"))
    return findings


def _require_runnable(key: str, item: dict) -> None:
    """Raise unless ``item`` names a check kind with the parameters it needs."""
    check = item.get("check")
    if check not in CHECKS:
        raise ValueError(
            f"titles.yaml formats.{key}: validation {_rule_text(item)!r} names "
            f"check {check!r}, which nothing runs (known: {', '.join(sorted(CHECKS))})."
        )
    if check in (CHECK_FORBID, CHECK_REQUIRE):
        regex = item.get("regex")
        if not isinstance(regex, str) or not regex:
            raise ValueError(f"titles.yaml formats.{key}: {check} check without a `regex`.")
        try:
            re.compile(regex)
        except re.error as exc:
            raise ValueError(
                f"titles.yaml formats.{key}: {check} regex {regex!r} does not compile: {exc}."
            ) from exc
    if check in (CHECK_MIN_LENGTH, CHECK_MAX_LENGTH):
        length = item.get("length")
        if not isinstance(length, int) or isinstance(length, bool) or length < 1:
            raise ValueError(
                f"titles.yaml formats.{key}: {check} check without a positive `length`."
            )


def _violation(check: str, item: dict, text: str) -> str | None:
    """What about ``text`` violates the check, or ``None`` when it passes."""
    if check == CHECK_FORBID:
        found = re.search(item["regex"], text)
        return f"found {found.group(0)!r} in {text!r}" if found else None
    if check == CHECK_REQUIRE:
        return None if re.search(item["regex"], text) else f"not found in {text!r}"
    length = len(text)
    if check == CHECK_MIN_LENGTH and length < item["length"]:
        return f"{text!r} is {length} characters"
    if check == CHECK_MAX_LENGTH and length > item["length"]:
        return f"{text!r} is {length} characters"
    return None


def _pattern_finding(key: str, declared: list[dict], pattern: str, title: str) -> TitleFinding:
    for item in declared:
        if item.get("check") == CHECK_PATTERN:
            return (
                _severity(item.get("severity"), SEVERITY_HARD_REJECT),
                _label(item),
                f"{_rule_text(item)} — {title!r} does not match {pattern!r}",
            )
    return (
        SEVERITY_HARD_REJECT,
        DEFAULT_PATTERN_LABEL,
        f"title {title!r} does not match the titles.yaml pattern for {key!r}: {pattern!r}",
    )


def _label(item: dict) -> str:
    name = item.get("name")
    return name if isinstance(name, str) and name else f"title.{item.get('check')}"


def _rule_text(item: dict) -> str:
    """The validation's prose rule on one line, without a trailing period."""
    return " ".join(str(item.get("rule") or "").split()).rstrip(".")


def _severity(token: object, default: str) -> str:
    """Parse a ``[validation-severity:<id>]`` token; ``default`` when absent or malformed."""
    match = _SEVERITY_TOKEN.fullmatch(token) if isinstance(token, str) else None
    return match.group(1) if match else default
