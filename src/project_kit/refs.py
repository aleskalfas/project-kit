"""Reference-graph operations across agents, skills, decisions, and hooks (per COR-013).

Walks the corpus, builds an in-memory reference graph, and exposes
queries:

- Bidirectional consistency: every frontmatter declaration must surface
  in the body; every body reference must be declared in frontmatter.
- Hook closure: every `needs:` must be answered by some `answers:`
  (skill) or `provides:` (package.yaml). Same-tier collisions surface.
- Read-only lookups: show outgoing refs, reverse lookup, record-ID
  resolution, hook resolution by precedence.

Body parser convention (per COR-013, documented in `.pkit/agents/README.md`):

- Paths inside backticks: `` `.pkit/foo.md` `` — matched when the text
  looks path-like (contains `/` or a recognised extension).
- Markdown link targets: `[text](relative/path.md)` — URLs are skipped.
- Record IDs as bare tokens: `COR-NNN`, `PRJ-NNN`.
- Hook names: `<topic>.<operation>` or `<topic>.<provider>.<operation>`.
- Skipped regions: fenced code blocks, HTML comments, strikethrough.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ruamel.yaml import YAML

Kind = Literal["agent", "skill"]
Namespace = Literal["core", "project"]


@dataclass(frozen=True)
class Declared:
    """References declared in an artifact's frontmatter."""

    reads_paths: frozenset[str] = field(default_factory=frozenset)
    reads_records: frozenset[str] = field(default_factory=frozenset)
    reads_patterns: frozenset[str] = field(default_factory=frozenset)
    owns: frozenset[str] = field(default_factory=frozenset)
    needs: frozenset[str] = field(default_factory=frozenset)
    answers: frozenset[str] = field(default_factory=frozenset)
    gates: frozenset[str] = field(default_factory=frozenset)
    storyboards: frozenset[str] = field(default_factory=frozenset)
    # `composes` — for composite skills per COR-020. Each entry is a path
    # relative to the skill's folder, naming a part of the composite
    # (sub-procedure markdown, script, template, reference doc).
    # Validated for existence; not bidirectional-checked against body refs.
    composes: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class BodyRefs:
    """References extracted from an artifact's body prose."""

    paths: frozenset[str] = field(default_factory=frozenset)
    records: frozenset[str] = field(default_factory=frozenset)
    hooks: frozenset[str] = field(default_factory=frozenset)
    # Capability decision citations: (capability-name, decision-filename-stem)
    # extracted from `[<capability>:<filename-stem>]` body tokens per COR-017.
    capability_citations: frozenset[tuple[str, str]] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Artifact:
    """A file-bearing artifact (agent or skill) with its parsed references."""

    kind: Kind
    name: str
    namespace: Namespace
    path: Path  # absolute or target-root-relative
    declared: Declared
    body_refs: BodyRefs
    # When the artifact lives under `.pkit/capabilities/<cap>/`, the
    # owning capability name; None for area-shipped artifacts. The
    # `namespace` field is set to "core" for capability artifacts (they
    # are kit-shipped, not adopter-authored) but `capability` is the
    # authoritative discriminator for capability-owned content.
    capability: str | None = None


@dataclass(frozen=True)
class Provider:
    """A hook-provider entry: skill that answers, or a package.yaml that provides."""

    hook: str
    tier: Literal["project", "capability", "adapter", "core"]
    source: str  # human-readable origin: skill name, capability name, adapter name
    implementation: str  # `/skill-name` or shell command (for package.yaml providers)


@dataclass(frozen=True)
class Issue:
    """A validation finding. Mirrors `validate.Issue` for compatibility."""

    location: str
    diagnosis: str


# ---------------------------------------------------------------- public API


def load_artifacts(target_root: Path) -> list[Artifact]:
    """Walk agents and skills areas + installed capabilities; parse each.

    Walks two roots:
    - Area subtrees: `.pkit/{agents,skills}/{core,project}/`.
    - Capability subtrees (per COR-017): `.pkit/capabilities/<cap>/{agents,skills}/`.
      Capability artifacts are tagged with `capability=<cap-name>` and
      reported with `namespace="core"` (they ship via the methodology
      core, not adopter authorship).
    """
    artifacts: list[Artifact] = []
    for kind, area in (("agent", "agents"), ("skill", "skills")):
        for ns in ("core", "project"):
            ns_dir = target_root / ".pkit" / area / ns
            if not ns_dir.is_dir():
                continue
            for entry in sorted(ns_dir.iterdir()):
                file_path = _resolve_artifact_file(entry)
                if file_path is None:
                    continue
                artifacts.append(_load_one(kind, ns, file_path))  # type: ignore[arg-type]

    caps_dir = target_root / ".pkit" / "capabilities"
    if caps_dir.is_dir():
        for cap_dir in sorted(caps_dir.iterdir()):
            if not cap_dir.is_dir():
                continue
            cap_name = cap_dir.name
            for kind, sub in (("agent", "agents"), ("skill", "skills")):
                sub_dir = cap_dir / sub
                if not sub_dir.is_dir():
                    continue
                for entry in sorted(sub_dir.iterdir()):
                    file_path = _resolve_artifact_file(entry)
                    if file_path is None:
                        continue
                    artifacts.append(
                        _load_one(kind, "core", file_path, capability=cap_name)  # type: ignore[arg-type]
                    )

    return artifacts


def load_hook_providers(target_root: Path) -> list[Provider]:
    """Walk skills (`answers:`) and capability/adapter `package.yaml` (`provides:`)."""
    providers: list[Provider] = []

    # Skills: an `answers:` entry per hook name. Tier is "project" if from
    # the project namespace, "core" otherwise.
    for artifact in load_artifacts(target_root):
        if artifact.kind != "skill":
            continue
        tier: Literal["project", "core"] = (
            "project" if artifact.namespace == "project" else "core"
        )
        for hook in artifact.declared.answers:
            providers.append(
                Provider(hook=hook, tier=tier, source=artifact.name, implementation=f"/{artifact.name}")
            )

    # Capabilities and adapters: package.yaml may declare `provides: {hook: impl}`.
    for kind, glob in (("capability", "*/package.yaml"), ("adapter", "*/package.yaml")):
        base = target_root / ".pkit" / ("adapters" if kind == "adapter" else "capabilities")
        if not base.is_dir():
            continue
        for pkg in sorted(base.glob(glob)):
            data = _read_yaml(pkg)
            if not isinstance(data, dict):
                continue
            provides = data.get("provides") or {}
            if not isinstance(provides, dict):
                continue
            component = data.get("component") or {}
            name = component.get("name", pkg.parent.name) if isinstance(component, dict) else pkg.parent.name
            tier: Literal["capability", "adapter"] = "capability" if kind == "capability" else "adapter"  # type: ignore[no-redef]
            for hook, impl in provides.items():
                if isinstance(hook, str) and isinstance(impl, str):
                    providers.append(Provider(hook=hook, tier=tier, source=name, implementation=impl))

    return providers


def validate_corpus(target_root: Path) -> list[Issue]:
    """Run bidirectional consistency + hook closure + same-tier collision + storyboard + capability-citation + composes checks."""
    artifacts = load_artifacts(target_root)
    providers = load_hook_providers(target_root)
    issues: list[Issue] = []
    issues.extend(_validate_bidirectional(artifacts, target_root))
    issues.extend(_validate_hook_closure(artifacts, providers))
    issues.extend(_validate_same_tier_collisions(providers))
    issues.extend(_validate_storyboards(artifacts, target_root))
    issues.extend(_validate_capability_citations(artifacts, target_root))
    issues.extend(_validate_composes(artifacts, target_root))
    return issues


def resolve_record(target_root: Path, record_id: str) -> Path | None:
    """Resolve `COR-005` / `PRJ-NNN` / `ADR-NNN` to the matching record file, or None."""
    if not RECORD_RE.match(record_id):
        return None
    if record_id.startswith("COR-"):
        decisions_dir = target_root / ".pkit" / "decisions" / "core"
    elif record_id.startswith("PRJ-"):
        decisions_dir = target_root / ".pkit" / "decisions" / "project"
    else:  # ADR — resolved via overlay; gracefully degrade if unconfigured
        decisions_dir = _adr_records_dir_or_none(target_root)
        if decisions_dir is None:
            return None
    if not decisions_dir.is_dir():
        return None
    matches = sorted(decisions_dir.glob(f"{record_id}-*.md"))
    if matches:
        return matches[0]
    return None


def _adr_records_dir_or_none(target_root: Path) -> Path | None:
    """Soft variant of `decisions.resolve_adr_records_dir` for read-only uses.

    Returns None instead of raising when the overlay is missing/misconfigured
    or the directory doesn't exist. Used by `resolve_record` and the status-
    indexer so reference validation doesn't hard-fail on adopters who haven't
    opted into ADRs yet.
    """
    from project_kit.decisions import resolve_adr_records_dir

    try:
        return resolve_adr_records_dir(target_root)
    except Exception:  # noqa: BLE001 — soft resolve; any failure means "not configured"
        return None


def resolve_hook(providers: list[Provider], hook: str) -> Provider | None:
    """Pick the winning provider for a hook by precedence (project > capability > adapter > core)."""
    candidates = [p for p in providers if p.hook == hook]
    if not candidates:
        return None
    order = {"project": 0, "capability": 1, "adapter": 2, "core": 3}
    candidates.sort(key=lambda p: order.get(p.tier, 99))
    return candidates[0]


def who_references(artifacts: list[Artifact], target: str) -> list[Artifact]:
    """Reverse lookup: which artifacts reference `target`?

    `target` may be a path string, a record ID, a hook name, a pattern name,
    a storyboard path, or a capability citation in `<cap>:<stem>` form.
    Match against both declared and body refs.
    """
    matches: list[Artifact] = []
    for art in artifacts:
        cap_citations_flat = frozenset(
            f"{cap}:{stem}" for cap, stem in art.body_refs.capability_citations
        )
        all_refs = (
            art.declared.reads_paths
            | art.declared.reads_records
            | art.declared.reads_patterns
            | art.declared.owns
            | art.declared.needs
            | art.declared.answers
            | art.declared.gates
            | art.declared.storyboards
            | art.body_refs.paths
            | art.body_refs.records
            | art.body_refs.hooks
            | cap_citations_flat
        )
        if target in all_refs:
            matches.append(art)
    return matches


def find_rot(target_root: Path, artifacts: list[Artifact]) -> list[Issue]:
    """List references to superseded records, dropped scratchpads, or missing files.

    Three categories:
    - **Superseded records** — an artifact still cites a record whose
      `status:` is `superseded`. The methodology requires moving to the
      superseding record.
    - **Dropped scratchpads** — an artifact cites a scratchpad note that
      retired to `dropped/` (per COR-012). The thinking was abandoned;
      the reference shouldn't persist.
    - **Missing local paths** — an artifact cites a relative or
      project-rooted path that no longer resolves on disk.

    External URLs and template placeholders are not checked here.
    """
    issues: list[Issue] = []
    record_status_index = _index_decision_statuses(target_root)
    dropped_slugs = _index_dropped_scratchpad_slugs(target_root)

    for art in artifacts:
        loc = (
            str(art.path.relative_to(target_root)) if target_root in art.path.parents else str(art.path)
        )
        all_records = art.declared.reads_records | art.declared.gates | art.body_refs.records
        all_paths = art.declared.reads_paths | art.declared.owns | art.body_refs.paths

        for rec in sorted(all_records):
            status = record_status_index.get(rec)
            if status == "superseded":
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"references superseded record {rec!r}.",
                    )
                )

        for path in sorted(all_paths):
            # Skip pattern placeholders and anchors.
            if path.startswith(("<", "#", "http://", "https://")):
                continue
            # Scratchpad dropped check runs first: even if the file
            # exists at the cited path (it does, in dropped/), the
            # reference is still rotten — the thinking was abandoned.
            slug = _slug_from_scratchpad_path(path)
            if slug is not None and slug in dropped_slugs:
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"references dropped scratchpad note {path!r}.",
                    )
                )
                continue
            candidate = target_root / path if not Path(path).is_absolute() else Path(path)
            if candidate.exists():
                continue
            issues.append(
                Issue(
                    location=loc,
                    diagnosis=f"references missing path {path!r} (file does not exist).",
                )
            )

    return issues


def _index_decision_statuses(target_root: Path) -> dict[str, str]:
    """Map every decision ID (COR-NNN / PRJ-NNN / ADR-NNN) to its current status."""
    index: dict[str, str] = {}
    dirs: list[Path] = [
        target_root / ".pkit" / "decisions" / "core",
        target_root / ".pkit" / "decisions" / "project",
    ]
    adr_dir = _adr_records_dir_or_none(target_root)
    if adr_dir is not None:
        dirs.append(adr_dir)
    for decisions_dir in dirs:
        if not decisions_dir.is_dir():
            continue
        for record in sorted(decisions_dir.glob("*.md")):
            text = record.read_text(encoding="utf-8")
            fm, _ = _split_frontmatter(text)
            rid = fm.get("id")
            status = fm.get("status")
            if isinstance(rid, str) and isinstance(status, str):
                index[rid] = status
    return index


def _index_dropped_scratchpad_slugs(target_root: Path) -> set[str]:
    dropped_dir = target_root / ".pkit" / "scratchpad" / "dropped"
    if not dropped_dir.is_dir():
        return set()
    return {p.stem.split("-", 3)[-1] for p in dropped_dir.glob("*.md") if "-" in p.stem}


def _slug_from_scratchpad_path(path: str) -> str | None:
    """If path looks like a scratchpad note path, return its slug."""
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[0] != ".pkit" or parts[1] != "scratchpad":
        return None
    name = parts[-1]
    if not name.endswith(".md"):
        return None
    stem = name[: -len(".md")]
    if "-" not in stem:
        return None
    return stem.split("-", 3)[-1]


def rename_reference(
    target_root: Path,
    old: str,
    new: str,
    *,
    dry_run: bool = False,
) -> list[Path]:
    """Bulk rewrite a reference value across every artifact.

    Touches frontmatter list entries (`reads.{paths,records,patterns}`,
    `owns`, `needs`, `answers`, `gates`) and body references (backticked
    paths, markdown link targets, bare record IDs, hook tokens). Uses
    ruamel.yaml round-trip mode for the frontmatter so comments and
    formatting survive.

    Returns the list of files modified (empty in dry-run mode).
    """
    if not old or not new:
        raise click.ClickException("rename: both old and new values must be non-empty.")
    if old == new:
        return []

    rewriter = _Rewriter(old=old, new=new)
    modified: list[Path] = []
    artifacts = load_artifacts(target_root)
    for art in artifacts:
        text = art.path.read_text(encoding="utf-8")
        # Quick check: does the old token literally appear anywhere in
        # the file? If not, the rewriter won't change anything, and we
        # avoid round-tripping the YAML (which can mutate whitespace).
        if old not in text:
            continue
        new_text = rewriter.rewrite(text)
        if new_text != text:
            modified.append(art.path)
            if not dry_run:
                art.path.write_text(new_text, encoding="utf-8")
    return modified


class _Rewriter:
    """Rewrites occurrences of `old` to `new` in frontmatter + body.

    The split is mechanical: we slice on the `---` delimiters, run
    ruamel.yaml round-trip on the frontmatter (preserves comments,
    quoting, ordering), and run a contextual string replace on the body.
    Body replace uses simple substring substitution but bounded:
    - Backticked tokens (``...``): exact match between the backticks.
    - Link targets `[text](target)`: exact match for `target`.
    - Bare record IDs / hook tokens: word-boundary match.
    """

    def __init__(self, old: str, new: str) -> None:
        self.old = old
        self.new = new
        self._kind = self._classify(old)

    @staticmethod
    def _classify(token: str) -> str:
        if RECORD_RE.match(token):
            return "record"
        if HOOK_TOKEN_RE.fullmatch(token) and not token in _YAML_FIELD_PATHS:
            return "hook"
        return "path"

    def rewrite(self, text: str) -> str:
        if not text.startswith("---"):
            # No frontmatter — body-only.
            return self._rewrite_body(text)
        after = text[len("---") :].lstrip("\n")
        end = re.search(r"^---\s*$", after, re.MULTILINE)
        if not end:
            return self._rewrite_body(text)
        fm_yaml = after[: end.start()]
        body = after[end.end() :].lstrip("\n")
        new_fm = self._rewrite_frontmatter(fm_yaml)
        new_body = self._rewrite_body(body)
        return f"---\n{new_fm}---\n\n{new_body}"

    def _rewrite_frontmatter(self, fm_yaml: str) -> str:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        data = yaml.load(io.StringIO(fm_yaml))
        if data is None:
            return fm_yaml
        self._walk_yaml(data)
        out = io.StringIO()
        yaml.dump(data, out)
        return out.getvalue()

    def _walk_yaml(self, node: Any) -> None:
        if isinstance(node, list):
            for i, item in enumerate(node):
                if isinstance(item, str) and item == self.old:
                    node[i] = self.new
                else:
                    self._walk_yaml(item)
        elif isinstance(node, dict):
            for k, v in list(node.items()):
                if isinstance(v, str) and v == self.old:
                    node[k] = self.new
                else:
                    self._walk_yaml(v)

    def _rewrite_body(self, body: str) -> str:
        old, new = self.old, self.new
        if self._kind == "record":
            # Bare record tokens — word boundaries.
            return re.sub(rf"\b{re.escape(old)}\b", new, body)
        if self._kind == "hook":
            # Word boundaries again — hook tokens are surrounded by
            # whitespace or punctuation but not other alnum.
            return re.sub(rf"\b{re.escape(old)}\b", new, body)
        # Path — replace in backticks and in link targets, leave free
        # prose alone (path strings rarely appear unwrapped).
        backtick = re.compile(rf"`{re.escape(old)}`")
        body = backtick.sub(f"`{new}`", body)
        link = re.compile(rf"(\]\(){re.escape(old)}(\))")
        body = link.sub(rf"\1{new}\2", body)
        return body


def emit_graph_dot(artifacts: list[Artifact]) -> str:
    """Emit the reference graph as a Graphviz DOT document.

    Nodes are artifacts (agents + skills). Edges are references; edge
    labels indicate the bucket (reads.paths, gates, needs, etc.).
    Only declared (frontmatter) refs become edges — body refs are noise
    for visualisation and would clutter the graph.
    """
    lines: list[str] = ["digraph refs {", '  rankdir="LR";', '  node [shape=box, fontname="monospace"];']
    for art in artifacts:
        label = f"{art.kind}\\n{art.name}"
        shape = "oval" if art.kind == "skill" else "box"
        lines.append(f'  "{art.kind}/{art.name}" [label="{label}", shape={shape}];')

    for art in artifacts:
        src = f"{art.kind}/{art.name}"
        for ref in art.declared.reads_paths:
            lines.append(f'  "{src}" -> "{ref}" [label="reads.paths"];')
        for ref in art.declared.reads_records:
            lines.append(f'  "{src}" -> "{ref}" [label="reads.records"];')
        for ref in art.declared.owns:
            lines.append(f'  "{src}" -> "{ref}" [label="owns"];')
        for ref in art.declared.gates:
            lines.append(f'  "{src}" -> "{ref}" [label="gates"];')
        for ref in art.declared.needs:
            lines.append(f'  "{src}" -> "{ref}" [label="needs", style=dashed];')
        for ref in art.declared.answers:
            lines.append(f'  "{src}" -> "{ref}" [label="answers", style=dashed];')
        for ref in art.declared.storyboards:
            # Storyboards are runtime-readable load-bearing refs; bold to
            # set them apart visually from the other reference buckets.
            lines.append(f'  "{src}" -> "{ref}" [label="storyboards", style=bold];')
    lines.append("}")
    return "\n".join(lines)


def emit_graph_text(artifacts: list[Artifact]) -> str:
    """Emit the reference graph as a human-readable text outline."""
    lines: list[str] = []
    for art in sorted(artifacts, key=lambda a: (a.kind, a.namespace, a.name)):
        lines.append(f"{art.kind} {art.namespace}/{art.name}")
        for bucket, items in outgoing_refs(art).items():
            if not items:
                continue
            lines.append(f"  {bucket}:")
            for item in items:
                lines.append(f"    {item}")
    return "\n".join(lines)


def emit_graph_ascii(artifacts: list[Artifact]) -> str:
    """Emit the reference graph as a tree-style ASCII diagram.

    Each artifact becomes its own subtree with one branch per non-empty
    outgoing-refs bucket. Uses Unicode box-drawing characters (├── └── │)
    so the structure is visible at a glance in any terminal; same shape
    as `tree` command output. Empty buckets are omitted.
    """
    sorted_arts = sorted(artifacts, key=lambda a: (a.kind, a.namespace, a.name))
    lines: list[str] = []
    for index, art in enumerate(sorted_arts):
        if index > 0:
            lines.append("")
        lines.append(f"{art.kind} {art.namespace}/{art.name}")
        buckets = [(k, v) for k, v in outgoing_refs(art).items() if v]
        for bucket_idx, (bucket, items) in enumerate(buckets):
            is_last_bucket = bucket_idx == len(buckets) - 1
            bucket_prefix = "└──" if is_last_bucket else "├──"
            child_indent = "    " if is_last_bucket else "│   "
            lines.append(f"{bucket_prefix} {bucket}")
            for item_idx, item in enumerate(items):
                is_last_item = item_idx == len(items) - 1
                item_prefix = "└──" if is_last_item else "├──"
                lines.append(f"{child_indent}{item_prefix} {item}")
    return "\n".join(lines)


def outgoing_refs(artifact: Artifact) -> dict[str, list[str]]:
    """A flat per-bucket dump of the artifact's outgoing references."""
    return {
        "reads.paths": sorted(artifact.declared.reads_paths),
        "reads.records": sorted(artifact.declared.reads_records),
        "reads.patterns": sorted(artifact.declared.reads_patterns),
        "owns": sorted(artifact.declared.owns),
        "needs": sorted(artifact.declared.needs),
        "answers": sorted(artifact.declared.answers),
        "gates": sorted(artifact.declared.gates),
        "storyboards": sorted(artifact.declared.storyboards),
        "body.paths": sorted(artifact.body_refs.paths),
        "body.records": sorted(artifact.body_refs.records),
        "body.hooks": sorted(artifact.body_refs.hooks),
        "body.capability-citations": sorted(
            f"{cap}:{stem}" for cap, stem in artifact.body_refs.capability_citations
        ),
    }


# ---------------------------------------------------------------- parsing


RECORD_RE = re.compile(r"^(COR|PRJ|ADR)-\d+$")
RECORD_TOKEN_RE = re.compile(r"\b(?:COR|PRJ|ADR)-\d+\b")
HOOK_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*){1,2}\b")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCED_BLOCK_RE = re.compile(r"^(```|~~~).*?\n.*?^\1", re.MULTILINE | re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
STRIKETHROUGH_RE = re.compile(r"~~[^~\n]+~~")

# Capability decision citation per COR-017: `[<capability>:<decision-stem>]`.
# Capability name: kebab-case, 2+ chars, no trailing dash.
# Decision stem: `DEC-NNN` optionally followed by `-<slug>` segments.
CAP_CITATION_RE = re.compile(
    r"\[([a-z][a-z0-9-]*[a-z0-9]):(DEC-\d+(?:-[a-z0-9-]+)*)\]"
)

# Backtick text that *looks like* a path. Heuristic: contains a `/` OR
# ends with a recognised extension. Avoids matching command examples
# like `pkit init`.
_PATH_EXT_RE = re.compile(r"\.(md|sh|py|ya?ml|json|toml|txt|js|ts|rs|go|sql|html|css)$")

# A literal path must not contain template placeholders or ellipses.
# These shapes are illustrative (`.pkit/agents/<name>.md`, `.pkit/skills/...`)
# and the validator should ignore them rather than demand they be declared.
_TEMPLATE_MARKER_RE = re.compile(r"[<>]|\.{3}|\{|\}|\*")

# Names of YAML schema fields that are dotted (look hook-shaped) but
# refer to frontmatter structure, not hook names. The body often cites
# these when describing the schema (`the \`reads.records\` field`).
# Without this skip, every "frontmatter `reads.records`" mention in
# documentation prose would be flagged as an undeclared hook.
_YAML_FIELD_PATHS = frozenset(
    {
        "reads.paths",
        "reads.records",
        "reads.patterns",
        "metadata.wraps_command",
        "metadata.wraps_commands",
        "metadata.depends_on",
        "component.kind",
        "component.name",
        "component.version",
        # Schema mechanism YAML field paths (per COR-018's source block).
        "source.upstream",
        "source.commit",
        "source.decisions",
        "source.captured_at",
    }
)

# Common English abbreviations that match the hook-token regex
# superficially (`e.g`, `i.e`, etc.). Treating them as hooks would
# pollute the body-refs extraction.
_HOOK_FALSE_POSITIVES = frozenset(
    {
        "e.g",
        "i.e",
        "vs",
        "etc",
        "et.al",
    }
)


def _is_path_like(text: str) -> bool:
    """A backticked or linked token is path-like if it's specific enough.

    Heuristic: must contain a `/` separator and must not end in `/`
    (directory shorthand). Bare filenames like `README.md` or
    `package.yaml` are too generic to be tracked as references — they
    usually refer to "any README/package", not a specific file.
    """
    if _TEMPLATE_MARKER_RE.search(text):
        return False
    if "/" not in text:
        return False
    if text.endswith("/"):
        return False
    return True


_FILE_EXT_TAIL_RE = re.compile(
    r"\.(md|sh|py|ya?ml|json|toml|txt|js|ts|rs|go|sql|html|css)$"
)


def _is_hook_like(text: str) -> bool:
    """A token must match the hook regex AND not be a YAML-field path, file path, or abbreviation.

    File extensions (`core.md`, `overlay.yaml`, `package.yaml`) match the
    bare hook pattern superficially but are clearly paths; reject them.
    Common English abbreviations (`e.g`, `i.e`, etc.) also match the
    regex but are noise; reject them via the explicit blocklist.
    """
    if text in _YAML_FIELD_PATHS:
        return False
    if text in _HOOK_FALSE_POSITIVES:
        return False
    if _FILE_EXT_TAIL_RE.search(text):
        return False
    return bool(HOOK_TOKEN_RE.fullmatch(text))


def _is_url(text: str) -> bool:
    return text.startswith(("http://", "https://", "mailto:", "ftp://", "#"))


def extract_body_refs(body: str) -> BodyRefs:
    """Apply the COR-013 parser convention to extract path / record / hook / capability refs."""
    stripped = _strip_skip_regions(body)
    paths: set[str] = set()
    records: set[str] = set()
    hooks: set[str] = set()
    capability_citations: set[tuple[str, str]] = set()

    # Capability citations first — `[cap:DEC-NNN-slug]` per COR-017.
    # Run before the link extractor so the `[...]` shape isn't confused
    # with a markdown link (which requires `(target)`); it wouldn't
    # match anyway, but running first keeps the contract clear.
    for match in CAP_CITATION_RE.finditer(stripped):
        capability_citations.add((match.group(1), match.group(2)))

    for match in BACKTICK_RE.finditer(stripped):
        inner = match.group(1).strip()
        if _is_path_like(inner):
            paths.add(inner)
            continue
        # Backticked tokens may also surface record IDs or hook names.
        if RECORD_TOKEN_RE.fullmatch(inner):
            records.add(inner)
            continue
        if _is_hook_like(inner):
            hooks.add(inner)

    for match in LINK_RE.finditer(stripped):
        target = match.group(1)
        if _is_url(target):
            continue
        if _TEMPLATE_MARKER_RE.search(target):
            continue
        paths.add(target)

    # Bare record IDs always count — the format `(COR|PRJ)-NNN` is too
    # specific to appear by accident.
    for match in RECORD_TOKEN_RE.finditer(stripped):
        records.add(match.group(0))

    # Bare hook tokens (outside backticks): match only when surrounded
    # by whitespace or sentence punctuation, NOT when embedded inside a
    # backticked region (already handled above). This keeps prose like
    # "the project-management.create-issue hook" working while not flagging
    # things like inline package-version strings, YAML field paths, or
    # file extensions embedded in larger paths.
    for match in HOOK_TOKEN_RE.finditer(stripped):
        token = match.group(0)
        if not _is_hook_like(token):
            continue
        # If the preceding character is `/`, this is a file path
        # fragment (e.g. `.pkit/rules/core.md`), not a standalone hook.
        # If preceded by `$`, the token is part of a JSON Schema
        # construct like `$defs.entry.properties` — also not a hook.
        start = match.start()
        if start > 0 and stripped[start - 1] in ("/", ".", "$"):
            continue
        hooks.add(token)

    return BodyRefs(
        paths=frozenset(paths),
        records=frozenset(records),
        hooks=frozenset(hooks),
        capability_citations=frozenset(capability_citations),
    )


def _strip_skip_regions(body: str) -> str:
    """Remove fenced code blocks, HTML comments, and strikethrough spans."""
    body = FENCED_BLOCK_RE.sub("", body)
    body = HTML_COMMENT_RE.sub("", body)
    body = STRIKETHROUGH_RE.sub("", body)
    return body


def extract_declared(frontmatter: dict[str, Any]) -> Declared:
    """Pull the typed reference buckets out of a frontmatter mapping.

    Tolerant: missing keys become empty sets; non-list values are coerced
    to single-element sets where sensible (a malformed value surfaces in
    the schema check elsewhere, not here).
    """
    reads = frontmatter.get("reads") or {}
    if not isinstance(reads, dict):
        reads = {}

    declared = Declared(
        reads_paths=frozenset(_as_strlist(reads.get("paths"))),
        reads_records=frozenset(_as_strlist(reads.get("records"))),
        reads_patterns=frozenset(_as_strlist(reads.get("patterns"))),
        owns=frozenset(_as_strlist(frontmatter.get("owns"))),
        needs=frozenset(_as_strlist(frontmatter.get("needs"))),
        answers=frozenset(_as_strlist(frontmatter.get("answers"))),
        gates=frozenset(_as_strlist(frontmatter.get("gates"))),
        storyboards=frozenset(_as_strlist(frontmatter.get("storyboards"))),
        composes=frozenset(_as_strlist(frontmatter.get("composes"))),
    )
    return declared


def _as_strlist(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return []


# ---------------------------------------------------------------- internals


def _resolve_artifact_file(entry: Path) -> Path | None:
    """Return the canonical `.md` for a flat or folder-form artifact."""
    name = entry.name
    if entry.is_file() and name.endswith(".md") and not name.startswith("."):
        return entry
    if entry.is_dir():
        inner = entry / f"{entry.name}.md"
        if inner.is_file():
            return inner
    return None


def _load_one(
    kind: Kind,
    namespace: Namespace,
    path: Path,
    *,
    capability: str | None = None,
) -> Artifact:
    text = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    declared = extract_declared(fm)
    body_refs = extract_body_refs(body)

    # For composite skills (folder-form per COR-015 with supporting
    # sibling files per COR-020), the canonical file is the dispatcher
    # and per-operation walkthroughs / reference docs live as siblings.
    # Citations in those siblings belong to the same composite skill
    # — union them into body_refs so the bidirectional rule (COR-013)
    # reconciles them against the dispatcher's frontmatter declarations.
    #
    # Discriminator: path.parent.name == path.stem (folder-form).
    if path.parent.name == path.stem:
        for sibling in sorted(path.parent.glob("*.md")):
            if sibling == path:
                continue
            try:
                sibling_text = sibling.read_text(encoding="utf-8")
            except OSError:
                continue
            # Sub-procedure files carry no frontmatter per COR-020, but
            # _split_frontmatter is safe either way (returns the full
            # text as body when no `---` block is present).
            _, sibling_body = _split_frontmatter(sibling_text)
            sibling_refs = extract_body_refs(sibling_body)
            body_refs = BodyRefs(
                paths=body_refs.paths | sibling_refs.paths,
                records=body_refs.records | sibling_refs.records,
                hooks=body_refs.hooks | sibling_refs.hooks,
                capability_citations=(
                    body_refs.capability_citations
                    | sibling_refs.capability_citations
                ),
            )

    # Name: the file stem (matches both flat and folder layouts).
    name = path.stem
    return Artifact(
        kind=kind,
        name=name,
        namespace=namespace,
        path=path,
        declared=declared,
        body_refs=body_refs,
        capability=capability,
    )


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    after = text[len("---") :].lstrip("\n")
    end_match = re.search(r"^---\s*$", after, re.MULTILINE)
    if not end_match:
        return {}, text
    fm_yaml = after[: end_match.start()]
    body = after[end_match.end() :].lstrip("\n")
    fm = _read_yaml_str(fm_yaml)
    if not isinstance(fm, dict):
        fm = {}
    return fm, body


def _read_yaml(path: Path) -> Any:
    return _read_yaml_str(path.read_text(encoding="utf-8"))


def _read_yaml_str(text: str) -> Any:
    yaml = YAML(typ="safe")
    return yaml.load(io.StringIO(text))


# ---------------------------------------------------------------- checks


def _validate_bidirectional(artifacts: list[Artifact], target_root: Path) -> list[Issue]:
    """Forward (frontmatter → body) + backward (body → frontmatter) coverage."""
    issues: list[Issue] = []
    for art in artifacts:
        loc = str(art.path.relative_to(target_root)) if target_root in art.path.parents else str(art.path)

        declared_paths_all = (
            art.declared.reads_paths | art.declared.owns | art.declared.storyboards
        )
        # Pattern tokens (`<category-name>`) often appear as `owns:` entries
        # and as backticked references in body. The body parser skips
        # template-marker tokens, so backward checks would otherwise demand
        # pattern declarations the parser never extracted. Drop pattern-shaped
        # entries from the literal-path set; they're checked via the pattern
        # block below.
        declared_paths_all = frozenset(p for p in declared_paths_all if not (p.startswith("<") and p.endswith(">")))
        declared_records_all = art.declared.reads_records | art.declared.gates
        declared_hooks_all = art.declared.needs | art.declared.answers

        # Forward: every declared ref appears in the body. Falls back to
        # literal text search for paths whose shape the parser doesn't
        # extract (bare filenames like `CONTRIBUTING.md` — too generic
        # for backward-direction tracking, but legitimate forward
        # references when explicitly declared).
        file_text_lazy: str | None = None

        def _in_file_text() -> str:
            nonlocal file_text_lazy
            if file_text_lazy is None:
                file_text_lazy = art.path.read_text(encoding="utf-8")
            return file_text_lazy

        for path in declared_paths_all:
            if path in art.body_refs.paths:
                continue
            if path in _in_file_text():
                continue
            issues.append(
                Issue(
                    location=loc,
                    diagnosis=f"frontmatter declares path {path!r} but body does not cite it.",
                )
            )
        for rec in declared_records_all:
            if rec not in art.body_refs.records:
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"frontmatter declares record {rec!r} but body does not cite it.",
                    )
                )
        for hk in declared_hooks_all:
            if hk not in art.body_refs.hooks:
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"frontmatter declares hook {hk!r} but body does not mention it.",
                    )
                )
        # Pattern tokens may live in `reads.patterns` or as `<...>` entries
        # in `owns:` and other path-buckets. Walk the union.
        pattern_names: set[str] = set(art.declared.reads_patterns)
        for p in art.declared.reads_paths | art.declared.owns:
            if p.startswith("<") and p.endswith(">"):
                pattern_names.add(p.strip("<>"))
        file_text = art.path.read_text(encoding="utf-8")
        for pat in pattern_names:
            if f"<{pat}>" not in file_text:
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"frontmatter declares pattern {pat!r} but it is not referenced anywhere.",
                    )
                )

        # Backward: every body ref is declared in frontmatter.
        for path in art.body_refs.paths:
            if path not in declared_paths_all and not _is_doc_link(path):
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"body cites path {path!r} but it is not declared in frontmatter `reads.paths` or `owns`.",
                    )
                )
        for rec in art.body_refs.records:
            if rec not in declared_records_all:
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"body cites record {rec!r} but it is not declared in frontmatter `reads.records` or `gates`.",
                    )
                )
        for hk in art.body_refs.hooks:
            if hk not in declared_hooks_all:
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"body mentions hook {hk!r} but it is not declared in frontmatter `needs` or `answers`.",
                    )
                )

    return issues


def _is_doc_link(path: str) -> bool:
    """Discriminator for paths the validator should *not* require to be declared.

    Some paths are illustrative (URL fragments, anchor links) or sibling
    documentation references that the bidirectional rule should allow
    without declaration. Conservative for now — only skips anchor-only
    refs (`#section`) and same-file refs (`./local.md`).
    """
    return path.startswith(("#", "./"))


def _validate_hook_closure(artifacts: list[Artifact], providers: list[Provider]) -> list[Issue]:
    """Every `needs:` hook must be answerable by at least one provider."""
    issues: list[Issue] = []
    provided_hooks = {p.hook for p in providers}
    for art in artifacts:
        for hook in art.declared.needs:
            if hook not in provided_hooks:
                # Use path-based location so capability artifacts surface
                # under `.pkit/capabilities/<cap>/...`, not under the
                # synthetic area path.
                target_root = _infer_target_root(art.path)
                loc = (
                    str(art.path.relative_to(target_root))
                    if target_root is not None and target_root in art.path.parents
                    else str(art.path)
                )
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"declares need for hook {hook!r} but no provider exists "
                        f"(skill `answers:` or package.yaml `provides:`).",
                    )
                )
    return issues


def _infer_target_root(path: Path) -> Path | None:
    """Walk up from `path` looking for a `.pkit` directory; return its parent.

    The artifact's path is absolute under the target root; the target
    root is the parent of `.pkit`. Used by location reporting when the
    validator doesn't have target_root in scope.
    """
    for ancestor in path.parents:
        if (ancestor / ".pkit").is_dir():
            return ancestor
    return None


def _validate_storyboards(artifacts: list[Artifact], target_root: Path) -> list[Issue]:
    """Validate the storyboard relationship per COR-016 (two-sided).

    Consumer side (today: agents):
    - Each declared storyboard path exists on disk.
    - The consumer body cites the path (load-bearing reference).
    - `Read` is in `tools` so the runtime can load the file.

    Storyboard side (frontmatter `consumers:`):
    - Frontmatter must be present and `consumers:` must be a non-empty list.
    - Each consumer entry must name an existing artifact whose `storyboards:`
      includes this storyboard's path (back-reference).
    - Storyboard files present in a consumer's folder must declare that
      consumer (orphan check).
    """
    issues: list[Issue] = []
    declared_storyboards: dict[str, list[Artifact]] = {}

    # Consumer-side checks (existing).
    for art in artifacts:
        if not art.declared.storyboards:
            continue
        loc = _location(art, target_root)
        file_text = art.path.read_text(encoding="utf-8")
        fm, body = _split_frontmatter(file_text)
        tools = fm.get("tools") or []
        if isinstance(tools, list) and "Read" not in tools:
            issues.append(
                Issue(
                    location=loc,
                    diagnosis="declares storyboards but `Read` is not in `tools`. "
                    "The runtime needs Read to load storyboards at session start.",
                )
            )
        for sb_path in sorted(art.declared.storyboards):
            declared_storyboards.setdefault(sb_path, []).append(art)
            candidate = target_root / sb_path if not Path(sb_path).is_absolute() else Path(sb_path)
            if not candidate.is_file():
                issues.append(
                    Issue(
                        location=loc,
                        diagnosis=f"declares storyboard {sb_path!r} but the file does not exist at that path.",
                    )
                )
                continue
            if sb_path in art.body_refs.paths:
                continue
            if sb_path in body:
                continue
            issues.append(
                Issue(
                    location=loc,
                    diagnosis=f"declares storyboard {sb_path!r} but the body does not cite it. "
                    "Load-bearing references must appear in the body so the runtime instruction is explicit.",
                )
            )

    # Storyboard-side checks. Walk every storyboard file in the agents
    # area and verify its `consumers:` frontmatter against the declared
    # back-references collected above.
    for storyboard_path in _walk_storyboard_files(target_root):
        rel = str(storyboard_path.relative_to(target_root))
        try:
            text = storyboard_path.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, _ = _split_frontmatter(text)

        consumers = fm.get("consumers") if isinstance(fm, dict) else None
        if not consumers or not isinstance(consumers, list):
            issues.append(
                Issue(
                    location=rel,
                    diagnosis="storyboard frontmatter is missing a non-empty `consumers:` list "
                    "(per COR-016). Declare which agent(s) drive this storyboard's scenarios.",
                )
            )
            continue

        # Each consumer entry must resolve to an existing consumer artifact,
        # and that consumer must declare this storyboard back.
        consumer_artifacts_found: list[Artifact] = []
        for entry in consumers:
            if not isinstance(entry, dict):
                issues.append(
                    Issue(
                        location=rel,
                        diagnosis=f"storyboard frontmatter `consumers:` entry is malformed: {entry!r}. "
                        "Each entry must be a mapping with `kind`, `name`, and `namespace`.",
                    )
                )
                continue
            kind = entry.get("kind")
            name = entry.get("name")
            ns = entry.get("namespace")
            if kind != "agent":
                issues.append(
                    Issue(
                        location=rel,
                        diagnosis=f"storyboard declares consumer of kind {kind!r}; "
                        "only `agent` is supported today (per COR-016).",
                    )
                )
                continue
            consumer = _find_agent(artifacts, name, ns)
            if consumer is None:
                issues.append(
                    Issue(
                        location=rel,
                        diagnosis=f"storyboard declares consumer agent {ns}/{name} but no such agent exists.",
                    )
                )
                continue
            consumer_artifacts_found.append(consumer)
            if rel not in consumer.declared.storyboards:
                issues.append(
                    Issue(
                        location=rel,
                        diagnosis=f"storyboard declares consumer agent {ns}/{name}, "
                        f"but that agent's `storyboards:` does not include this path. "
                        "Mutual declaration is required (per COR-016).",
                    )
                )

        # Orphan check: this storyboard sits in a folder; if no declared
        # consumer's folder matches, surface as a placement mismatch.
        parent = storyboard_path.parent
        # Folder-form agent siblings: parent dir contains <name>.md
        folder_owner_md = parent / f"{parent.name}.md"
        if folder_owner_md.is_file():
            owner_match = any(
                c.path == folder_owner_md for c in consumer_artifacts_found
            )
            if not owner_match and consumer_artifacts_found:
                issues.append(
                    Issue(
                        location=rel,
                        diagnosis=f"storyboard sits in {parent.relative_to(target_root)}/ "
                        f"but none of its declared consumers owns that folder. "
                        "Move the storyboard to its primary consumer's folder, or update consumers.",
                    )
                )

    # Orphan check from the other angle: storyboards on disk that NO
    # consumer's `storyboards:` declares.
    for storyboard_path in _walk_storyboard_files(target_root):
        rel = str(storyboard_path.relative_to(target_root))
        if rel not in declared_storyboards:
            issues.append(
                Issue(
                    location=rel,
                    diagnosis="storyboard file exists but no agent declares it in `storyboards:`. "
                    "Either delete the orphan, or add a `storyboards:` entry on the owning agent.",
                )
            )

    return issues


def _location(art: Artifact, target_root: Path) -> str:
    return (
        str(art.path.relative_to(target_root))
        if target_root in art.path.parents
        else str(art.path)
    )


def _walk_storyboard_files(target_root: Path) -> list[Path]:
    """All `storyboard.md` and `*.storyboard.md` files under .pkit/agents/."""
    agents_dir = target_root / ".pkit" / "agents"
    if not agents_dir.is_dir():
        return []
    found: list[Path] = []
    for path in agents_dir.rglob("*.md"):
        name = path.name
        if name == "storyboard.md" or name.endswith(".storyboard.md"):
            found.append(path)
    return sorted(found)


def _find_agent(artifacts: list[Artifact], name: str | None, namespace: str | None) -> Artifact | None:
    if not name:
        return None
    for art in artifacts:
        if art.kind != "agent":
            continue
        if art.name != name:
            continue
        if namespace is not None and art.namespace != namespace:
            continue
        return art
    return None


def _validate_capability_citations(
    artifacts: list[Artifact], target_root: Path
) -> list[Issue]:
    """Every `[<cap>:<stem>]` body citation must resolve to an installed capability decision.

    Per COR-017: capability decisions live at
    `.pkit/capabilities/<cap>/decisions/<stem>.md`. A citation that
    doesn't resolve means either (a) the capability isn't installed in
    this project, or (b) the decision filename has drifted. Both surface
    here so the author can fix the cite or install the capability.
    """
    issues: list[Issue] = []
    for art in artifacts:
        loc = _location(art, target_root)
        for cap_name, dec_stem in sorted(art.body_refs.capability_citations):
            decision_file = (
                target_root
                / ".pkit"
                / "capabilities"
                / cap_name
                / "decisions"
                / f"{dec_stem}.md"
            )
            if decision_file.is_file():
                continue
            issues.append(
                Issue(
                    location=loc,
                    diagnosis=f"cites capability decision [{cap_name}:{dec_stem}] but no file at "
                    f".pkit/capabilities/{cap_name}/decisions/{dec_stem}.md "
                    "(capability not installed, or decision renamed?).",
                )
            )
    return issues


def _validate_same_tier_collisions(providers: list[Provider]) -> list[Issue]:
    """Two providers in the same tier providing the same hook refuse rather than silently pick."""
    issues: list[Issue] = []
    grouped: dict[tuple[str, str], list[Provider]] = {}
    for p in providers:
        grouped.setdefault((p.hook, p.tier), []).append(p)
    for (hook, tier), entries in grouped.items():
        if len(entries) > 1:
            sources = ", ".join(sorted(e.source for e in entries))
            issues.append(
                Issue(
                    location=f"hooks/{hook}",
                    diagnosis=f"same-tier collision at tier '{tier}': "
                    f"multiple providers ({sources}). Disambiguate.",
                )
            )
    return issues


def _validate_composes(artifacts: list[Artifact], target_root: Path) -> list[Issue]:
    """Every `composes:` entry in a composite skill's frontmatter must exist on disk.

    Per COR-020, a composite skill declares each of its supporting files
    (sub-procedure markdown, scripts, templates, reference docs) in the
    dispatcher's `composes:` list. The paths are relative to the skill's
    folder. The validator confirms each listed file exists; missing
    entries usually indicate a recent refactor that left a stale entry,
    or a typo introduced at authoring time.

    Composes is structural inventory, not bidirectional-checked: a script
    listed in composes need not be cited in body prose.
    """
    issues: list[Issue] = []
    for art in artifacts:
        if not art.declared.composes:
            continue
        # Composes paths are relative to the skill's folder. The folder
        # is the canonical file's parent; for flat-form artifacts (no
        # folder), composes wouldn't make sense — flag the misuse.
        if art.path.parent.name != art.path.stem:
            issues.append(
                Issue(
                    location=_location(art, target_root),
                    diagnosis=f"declares `composes:` but {art.kind} is flat-form; "
                    f"composes only applies to folder-form composite skills "
                    f"(per COR-020). Migrate to folder layout per COR-015.",
                )
            )
            continue
        folder = art.path.parent
        for rel_path in sorted(art.declared.composes):
            sibling = folder / rel_path
            if sibling.exists():
                continue
            issues.append(
                Issue(
                    location=_location(art, target_root),
                    diagnosis=f"composes entry {rel_path!r} not found at "
                    f"{folder.relative_to(target_root)}/{rel_path}",
                )
            )
    return issues
