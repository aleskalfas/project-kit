#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Evidence-capability validator.

Walks a scope directory, parses `<scope>/evidence.yaml`, extracts every
`[ev:slug]` citation from `.md` and `.yaml` files in the sub-tree, and
verifies each cited slug resolves to a record. Hard-fail on cited-but-
missing; soft on orphans unless `--strict`. Contract per the capability's
DEC-003-validation-model.

Each scope is checked on its own (DEC-002): a directory below the scope
that holds an `evidence.yaml` of its own is a scope of its own, so the
walk leaves it out. Run on a directory that holds no `evidence.yaml`, the
validator checks the scope that directory lies in — the nearest directory
above it holding one — and errors only where no directory above holds one.

Self-contained via PEP 723 inline metadata: run via
`uv run --script .pkit/capabilities/evidence/scripts/validate.py <scope>`.
The first invocation installs the script's dependencies transparently;
adopters don't need a host pyproject.toml.

Exit codes:
  0  clean — every citation resolved
  1  one or more violations
  2  usage error (bad arguments, missing scope)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

CITATION_RE = re.compile(r"\[ev:([a-z0-9][a-z0-9-]*)\]")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# What may precede a fence on its line: indentation, block-quote markers and
# list markers, so a fence in a list item or a block quote is found too.
_FENCE_PREFIX = r"(?:[ \t]*(?:>|(?:[-+*]|\d{1,9}[.)])(?=[ \t])))*[ \t]*"
FENCE_OPEN_RE = re.compile(rf"^{_FENCE_PREFIX}(?P<fence>`{{3,}}|~{{3,}})(?P<info>.*)$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
EVIDENCE_FILE_NAME = "evidence.yaml"
IN_SCOPE_SUFFIXES = (".md", ".yaml", ".yml")
# Fenced code blocks (```/~~~) and HTML comments are *markdown* constructs;
# the skip-region stripping applies only to markdown. In YAML those characters
# are literal (e.g. inside a `notes: |` block scalar), so stripping them there
# would silently drop real citations sitting inside or after such content.
MARKDOWN_SUFFIXES = (".md",)
REQUIRED_RECORD_FIELDS = ("id", "source_url", "fetched_at", "excerpt")


@dataclass(frozen=True)
class Finding:
    """One validator finding — location plus diagnosis."""

    location: str
    diagnosis: str


@dataclass(frozen=True)
class Citation:
    """One cited slug, with where it was found."""

    slug: str
    file: Path
    line: int


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate [ev:slug] citations in a scope against its evidence.yaml.",
    )
    parser.add_argument(
        "scope",
        type=Path,
        help="Directory containing the evidence.yaml and the sub-tree to validate.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat orphan records (records not cited by any prose) as errors.",
    )
    args = parser.parse_args(argv)

    scope = args.scope.resolve()
    if not scope.is_dir():
        print(f"evidence: scope path is not a directory: {args.scope}", file=sys.stderr)
        return 2

    return _run(scope, strict=args.strict)


def _run(directory: Path, *, strict: bool) -> int:
    findings: list[Finding] = []

    # Step 1: find the scope the directory lies in — the nearest directory,
    # from the one named upwards, that holds an evidence.yaml (DEC-002).
    evidence_file = _scope_evidence_file(directory)
    if evidence_file is None:
        # No scope holds the directory. Walk citations anyway so the author
        # sees what's cited; report the missing evidence.yaml as the error
        # (DEC-003: an error only where no ancestor holds one).
        citations = _walk_citations(directory, None)
        if citations:
            findings.append(
                Finding(
                    location=EVIDENCE_FILE_NAME,
                    diagnosis=f"no evidence.yaml in this directory or any above it; "
                    f"{len(citations)} citation(s) in sub-tree have nowhere to resolve.",
                )
            )
        else:
            print(
                f"evidence: no evidence.yaml at {directory} or above it, and no "
                f"citations in sub-tree — nothing to validate.",
                file=sys.stderr,
            )
            return 0
        _print_findings(findings)
        return 1

    scope = evidence_file.parent
    if scope != directory:
        print(
            f"evidence: no evidence.yaml at {directory}; checking the scope it lies in, {scope}.",
            file=sys.stderr,
        )

    try:
        records = _load_records(evidence_file)
    except _EvidenceParseError as exc:
        print(
            f"evidence: {evidence_file.relative_to(scope.parent)} — {exc}",
            file=sys.stderr,
        )
        return 1

    # A record with no string `id` names nothing a citation can cite; step 2
    # reports it as a finding rather than failing on it here (DEC-003).
    record_ids = {r["id"]: r for r in records if isinstance(r.get("id"), str)}

    # Step 2: validate schema of each record (required fields, slug shape).
    for idx, record in enumerate(records, 1):
        for field in REQUIRED_RECORD_FIELDS:
            if field not in record or record[field] in (None, ""):
                findings.append(
                    Finding(
                        location=f"{evidence_file.name}#records[{idx}]",
                        diagnosis=f"record missing required field '{field}'.",
                    )
                )
        rec_id = record.get("id")
        if rec_id in (None, ""):
            continue
        if not isinstance(rec_id, str) or not SLUG_RE.match(rec_id):
            findings.append(
                Finding(
                    location=f"{evidence_file.name}#records[{idx}]",
                    diagnosis=f"record id {rec_id!r} is not kebab-case "
                    f"(must match {SLUG_RE.pattern}).",
                )
            )

    # Step 3: walk in-scope files for citations.
    citations = _walk_citations(scope, evidence_file)

    # Step 4: every citation must resolve.
    for cite in citations:
        if cite.slug not in record_ids:
            rel = cite.file.relative_to(scope) if scope in cite.file.parents else cite.file
            findings.append(
                Finding(
                    location=f"{rel}:{cite.line}",
                    diagnosis=f"cited slug {cite.slug!r} has no record.",
                )
            )

    # Step 5: orphan check (soft by default, hard under --strict).
    cited_slugs = {c.slug for c in citations}
    orphans = sorted(set(record_ids) - cited_slugs)
    if orphans and strict:
        for slug in orphans:
            findings.append(
                Finding(
                    location=evidence_file.name,
                    diagnosis=f"orphan record {slug!r} — defined but no citation references it.",
                )
            )

    # Report.
    if findings:
        _print_findings(findings)
        return 1

    suffix = ""
    if orphans:
        suffix = f" ({len(orphans)} orphan(s) — pass --strict to elevate to errors)"
    print(
        f"evidence: {len(citations)} citation(s) validated against "
        f"{evidence_file.relative_to(scope.parent)} — all resolved.{suffix}",
        file=sys.stderr,
    )
    return 0


def _scope_evidence_file(directory: Path) -> Path | None:
    """The evidence.yaml of the scope `directory` lies in, or None.

    That is the nearest one from `directory` upwards (DEC-002).
    """
    for candidate in (directory, *directory.parents):
        evidence_file = candidate / EVIDENCE_FILE_NAME
        if evidence_file.is_file():
            return evidence_file
    return None


def _in_scope_files(root: Path, evidence_file: Path | None) -> list[Path]:
    """The `.md` / `.yaml` / `.yml` files of the scope walked from `root`.

    Leaves out the scope's evidence.yaml itself, and each directory below
    `root` that holds an evidence.yaml of its own: that directory is a scope
    of its own, checked on its own run (DEC-002, DEC-003).
    """
    skip = evidence_file.resolve() if evidence_file is not None else None
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if not (here / d / EVIDENCE_FILE_NAME).is_file()]
        for name in filenames:
            path = here / name
            if path.suffix not in IN_SCOPE_SUFFIXES or not path.is_file():
                continue
            if skip is not None and path.resolve() == skip:
                continue
            paths.append(path)
    return sorted(paths)


def _walk_citations(scope: Path, evidence_file: Path | None) -> list[Citation]:
    """Find every [ev:slug] citation in scope's sub-tree, with line numbers.

    Skips the scope's evidence.yaml itself — excerpts may quote
    citation-shaped text from their source — and every nested scope.
    """
    citations: list[Citation] = []
    for path in _in_scope_files(scope, evidence_file):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        stripped, line_offsets = _strip_with_offsets(text, path.suffix)
        for match in CITATION_RE.finditer(stripped):
            slug = match.group(1)
            # Map stripped offset back to original line number.
            stripped_pos = match.start()
            line = _line_for_offset(line_offsets, stripped_pos)
            citations.append(Citation(slug=slug, file=path, line=line))
    return citations


def _strip_with_offsets(text: str, suffix: str) -> tuple[str, list[int]]:
    """Strip skip-regions and return (stripped_text, line_offsets).

    `line_offsets[i]` is the byte offset in `text` (the original) where
    line `i+1` starts. We use the original text to compute line numbers
    so reported lines match the source even after stripping. Stripping
    replaces each character in a skip region with a space (newlines
    preserved) so byte offsets — and therefore line numbers — survive.

    Fenced code blocks and HTML comments are stripped **only for markdown**
    files — they are markdown constructs. YAML files are scanned as raw text:
    in YAML, ``` and `<!-- -->` are literal characters (e.g. inside a
    `notes: |` block scalar), so stripping them would silently drop real
    citations sitting inside or after such content.
    """
    line_offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_offsets.append(i + 1)

    if suffix not in MARKDOWN_SUFFIXES:
        return text, line_offsets

    stripped = _blank_fenced_blocks(text)
    stripped = HTML_COMMENT_RE.sub(_blank_match, stripped)
    return stripped, line_offsets


def _blank_fenced_blocks(text: str) -> str:
    """Blank each fenced code block of a markdown text, fences included.

    A fence is a run of three or more backticks or tildes. It may stand
    indented, or after block-quote and list markers, as in a list item. It
    closes on a later line holding only a run of the same character at least
    as long. A fence that never closes is left as it stands, so a stray fence
    never hides the citations after it.
    """
    # Split on "\n" only, as the line offsets are counted.
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        opening = FENCE_OPEN_RE.match(lines[i].rstrip("\r"))
        if opening is not None:
            fence = opening.group("fence")
            # A backtick fence's info string holds no backtick (CommonMark):
            # "```a```" is inline code, not a fence.
            if not (fence[0] == "`" and "`" in opening.group("info")):
                closing = re.compile(
                    rf"^{_FENCE_PREFIX}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$"
                )
                end = next(
                    (j for j in range(i + 1, len(lines)) if closing.match(lines[j].rstrip("\r"))),
                    None,
                )
                if end is not None:
                    out.extend(_blank(line) for line in lines[i : end + 1])
                    i = end + 1
                    continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _blank(text: str) -> str:
    """Replace text with spaces of equal length, preserving newlines.

    Keeps line offsets stable so line numbers in the original text
    survive stripping.
    """
    return "".join(c if c in "\r\n" else " " for c in text)


def _blank_match(match: re.Match[str]) -> str:
    """Blank a regex match (see `_blank`)."""
    return _blank(match.group(0))


def _line_for_offset(line_offsets: list[int], offset: int) -> int:
    """Binary-search line_offsets for the 1-based line number containing `offset`."""
    lo, hi = 0, len(line_offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_offsets[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


class _EvidenceParseError(Exception):
    """Raised when evidence.yaml fails to parse or fails the wrapped-shape check."""


def _load_records(evidence_file: Path) -> list[dict[str, Any]]:
    """Parse evidence.yaml; return the records list.

    Tolerates an empty `records: []` (zero records is valid, just unusual).
    A missing `records`, or one with no value, is no list, so it is malformed
    (DEC-002's wrapped shape). Raises _EvidenceParseError on malformed input.
    """
    yaml = YAML(typ="safe")
    try:
        data = yaml.load(evidence_file.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise _EvidenceParseError(f"YAML parse error: {exc}") from exc
    except OSError as exc:
        raise _EvidenceParseError(f"could not read file: {exc}") from exc

    if not isinstance(data, dict):
        raise _EvidenceParseError(
            "top-level must be a mapping with 'schema_version' and 'records'."
        )
    if data.get("schema_version") != 1:
        raise _EvidenceParseError(
            f"unsupported schema_version: {data.get('schema_version')!r} (expected 1)."
        )
    if "records" not in data:
        raise _EvidenceParseError("no top-level 'records' list.")
    records = data["records"]
    if not isinstance(records, list):
        raise _EvidenceParseError("'records' must be a list.")
    cleaned: list[dict[str, Any]] = []
    for idx, rec in enumerate(records, 1):
        if not isinstance(rec, dict):
            raise _EvidenceParseError(f"records[{idx}] must be a mapping.")
        cleaned.append(rec)
    return cleaned


def _print_findings(findings: list[Finding]) -> None:
    for f in findings:
        print(f"{f.location} — {f.diagnosis}", file=sys.stderr)
    print(f"\nevidence: {len(findings)} violation(s); see above.", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
