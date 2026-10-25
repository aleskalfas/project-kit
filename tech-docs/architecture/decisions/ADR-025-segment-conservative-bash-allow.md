---
id: ADR-025
title: "Bash commands are read conservatively: grants as written, denies in listed forms, doubt never allows"
status: accepted
date: 2026-06-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

A Bash command reaches the permission decision core as one string, and this
ADR decides how the core reads it. The core allows a command only where a
grant covers every segment its dumb splitter yields, matched as written once
quotes are removed as the shell removes them (point 2), with no shell parser
(point 3). This ADR makes two widenings, each a prompt-reduction over
already-granted intent, **never a new grant**. A single leading `cd <path>` is
stripped before the core decides on the rest (point 1). A redirection that
writes no file is removed before the core reads the command (point 2): an fd
duplicated or closed, or output discarded to `/dev/null`. The core inherits
[ADR-004](ADR-004-autonomy-intent-confinement.md)'s fail-closed-on-uncertainty
stance: a segment it cannot read as the shell reads it, such as one holding an
expansion, any other redirection or an assignment that changes which program
runs, or whose command no privilege recognizes, makes it **abstain (prompt)**,
never allow, unless a deny binds on the words it reads (point 2). A deny also
binds on the forms point 5 lists, such as a long flag cut to a prefix. Where a
pathname pattern or a configuration assignment may make the command one a deny
names, the core cannot tell, and abstains (point 2). A configuration git reads,
or one `git -c` sets, stays the grant's breadth, and a program behind a
wrapper such as `env` is read as the wrapper (point 5). The code lives in the neutral core both the hook and the CLI
import (point 4).

**Decision in one line:** the core allows a Bash command only where a grant
covers every segment as written, after stripping one leading `cd` and each
redirection that writes no file; a deny binds on the command and on the forms
point 5 lists; and where the core cannot read the command as the shell does,
or cannot tell whether a deny binds, it never allows. A compound allowed
because each segment looks safe on its own, blind to how the segments compose,
is **rejected as unsound**, and any further widening is **deferred** under
[COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md) until a
demonstrated residual-prompt need earns it, as such a need earned the
redirections (point 6).

This is a **refinement child of [ADR-004](ADR-004-autonomy-intent-confinement.md)**,
not a supersession: the intent/confinement split, the fail-open hook + fail-closed
native double-lock, and the deny-side posture are all unchanged. Critically, the
deny side stays **porous** — this change does **not** promote the speed-bump to a
boundary. A future reader must not misread a tighter allow path as a hardened deny
path; the deny layer remains the speed-bump
[ADR-004](ADR-004-autonomy-intent-confinement.md) and
[ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md) describe.

## Context

The forcing question (issue #239, with a `critic` + `architect` review pass
behind it) is whether the permission decision core can stop prompting on a
compound Bash command whose *only* obstacle is a leading directory change. The
shared core (`.pkit/permissions/decide.py`) already segments a compound on
`&&` / `||` / `|` / `;` and strips a leading `export` / `VAR=` env prefix per
segment (the `segments()` helper fixed the `export GH_HOST=x && gh pr list`
false-prompt). It does **not** strip a leading `cd <path>`, so
`cd src && gh pr list` — where `gh pr list` is already granted — still prompts.

A second forcing question (issue #2002) is whether the core can stop prompting
on a granted command whose only obstacle is a redirection that writes no file,
as in `git status 2>/dev/null`. In October 2026 the maintainer reported
approving dozens of harmless prompts a session without reading them, so a
prompt no longer stopped a dangerous command. The PRJ-006 diagnostic log then
held 566 calls its report counts as real prompts, 458 of them for a command of
compound shape. Of the calls the core deferred, 132 gave a redirection as the
reason, 40 of them piped into `tail`, a shape that also needs a grant of
`tail`. The log redacts arguments, so it does not show which redirection each
call held.

The decision core is harness-neutral, propagated, and imported by **both** the
claude-code PreToolUse hook (which runs in the adopter tree at decision time,
under bare `python3` inside the macOS Seatbelt box per
[ADR-014](ADR-014-macos-sandbox-platform-stance.md)) and the `pkit permissions`
CLI. [ADR-002](ADR-002-permission-realizer-ownership.md) /
[ADR-003](ADR-003-permission-core-code-home.md) pin the **same-code invariant**:
hook and CLI must decide identically from one `decide()`. So any change to how a
compound is classified lives in that one neutral core, never in the adapter hook
— otherwise the two callers diverge.

This sits squarely inside [ADR-004](ADR-004-autonomy-intent-confinement.md)'s
intent axis. The hook inspects a command string; it cannot confine a shell
(`cd` / absolute-path escapes defeat any cwd check — ADR-004's "directory-scoped
bash grant is security theater"). That is precisely why the deny side is a
speed-bump, not a boundary, and why this ADR must not let a tighter allow path
read as a hardened deny path. The operational rule the change supports is
core.md rule 15 — *issue the narrowest action the layer can vet*: a single
`cd && <granted-cmd>` is a narrow, vettable action, and reducing its false prompt
is the rule's intent applied to the hot path.

As project-kit's own architecture-decision record, harness and code-home
specifics are in scope here, unlike the harness-neutral COR.

## Decision

**The decision core reads a Bash command conservatively: a grant must cover
every segment as written, after one leading `cd <path>` and each redirection
that writes no file are removed, and a deny binds on the forms point 5 lists.
Removing them is a prompt-reduction over already-granted intent, never a new
grant. Every uncertainty fails closed (abstain / prompt), never to auto-allow.
A rule blind to how segments compose is rejected as unsound, and any other
widening is deferred.**

### 1. Phase 1 — strip a leading `cd`, decide on the remainder

When the first
segment of a compound is a bare `cd <path>` (no quotes, no substitution,
no redirection but one that writes no file), the core drops it and evaluates
the remaining command against the grant model exactly as if it had been issued
alone. `cd src && gh pr list` with
`gh pr list` granted auto-approves; `cd src && rm -rf /` does not (the remainder
matches no allow and, for guardrail denies, the deny still binds). The strip is
one of the two widenings this ADR makes. The other is point 2's removal of a
redirection that writes no file, which the core makes before it looks for the
`cd`.

### 2. Inherited fail-closed-on-uncertainty (ADR-004 decision point 4), non-negotiable

Any segment the core cannot read as the shell reads it makes the core
**abstain (prompt)**: an expansion opened by a `$` or a backtick, a
substitution opened by a `(`, a `<` / `>` redirection other than one that
writes no file (below), a word the shell
splits, drops as a comment or brace-expands otherwise than the core reads it,
a leading assignment to a variable that changes which program runs or loads
code into it ahead of its own, such as `PATH` or `LD_PRELOAD`, a leading
assignment written with a quote or a backslash, an operand of `export` other
than a plain name or assignment, which the shell expands before `export` reads
it, a program name holding whitespace, which a recognizer's pattern would read
as two words, or an unrecognized command. It
NEVER auto-allows under uncertainty; a deny on the words it reads wins over any
such construct. The core looks for such a construct in the whole command, a
leading `cd` included, and strips no `cd` from a command that holds one
(point 1). A quote in an argument is no such construct. Before it matches a
grant or a deny, the core removes a word's quotes and backslashes as the shell
removes them, by the POSIX quoting rules of Python's standard library, so a
quoted word is matched as the word the shell runs, and `"--force"` is denied as
`--force` is.

A redirection that writes no file and changes no program is no such construct
either: an fd duplicated onto stdout or stderr or closed, such as `2>&1`, `>&2`
or `2>&-`, and output discarded to `/dev/null`, such as `>/dev/null`,
`2>/dev/null` or `&>/dev/null`. The core removes each such redirection by a
plain scan for it, before it splits the command, looks for any other
construct, or matches a grant or a deny on what is left, so a deny binds on a
program behind such a redirection. A form counts only as a whole word, or as an operator and
`/dev/null` with a space between, and only in a shape that writes no file in
bash, zsh or dash: each fd number is one digit or is left out, the word after
`>&` or `<&` is `1`, `2` or `-` alone, the target is exactly `/dev/null` and
unquoted, and `&>` or `&>>` stands last in its segment. A removal never leaves
a command of redirections and assignments alone, which zsh runs as the program
`NULLCMD` names: a segment so left, or left with only a word that opens a
command of its own, such as `{` or `do`, keeps the whole command untrusted. The scan
ignores quoting. Inside quotes such text is part of an argument, and removing
it changes only that argument's text, never a program, a flag or a separator,
since the whitespace around it stays. Any other redirection, such as `>|`,
`<>`, a here-string or a heredoc, stays untrusted.

For a grant, outside an operand of `export`, a pathname pattern
is matched as written: it changes only arguments, from the names of files, never
the program a grant names. An
assignment to a program's own setting, such as `GIT_PAGER`, is stripped like
any other: what a granted program is told to run is the grant's breadth, and a
`git` grant already lets `git -c core.fsmonitor=…` run any program. Where an
unquoted pathname pattern, or an assignment that changes which configuration
the program reads, such as `HOME` or `GIT_CONFIG_GLOBAL`, may make the command
one a deny names, the core cannot tell, and abstains whatever a grant allows.
It abstains rather than denies, as on any other construct it cannot read: a
deny would claim a match the core cannot see. Such an assignment is still a
program's own setting to a grant. For a deny, it counts on every command of
the program the deny names, since the configuration may hold an alias of any
name, and it counts where the shell hands it on: for the command it stands in
front of, and from a segment that only assigns or exports, for the segments
after it. The segment
splitter stays dumb; the conservatism lives in the classification, not in
parsing the shell's grammar.

### 3. No shell parser

The core keeps its dumb regex segmenter (`_SEP`). A real
shell parser is **rejected on altitude grounds**: the hook runs bare `python3`
in-sandbox ([ADR-014](ADR-014-macos-sandbox-platform-stance.md)), and importing
an adversarial-input parser into a fail-open, security-adjacent component trades
a bounded, auditable splitter for parsing fragility in the worst place to host
it. Removing a word's quotes by the POSIX quoting rules of Python's standard
library (point 2) is no such parser: it reads the words of one segment the
splitter found, never the shell's grammar. Where those rules read a word
otherwise than bash or zsh does by default — a `$` or a backtick inside double
quotes, `$'…'`, a backslash before a newline, a comment, a brace — the
construct is untrusted and no grant allows the command; a quote that does not
close is such a construct, and a fault abstains like any other. A shell option
that changes how quotes are read, such as zsh's `RC_QUOTES`, changes only the
text of an argument. Conservatism is achieved by abstaining on anything the
dumb splitter cannot trust, not by parsing harder.

### 4. Code home — the shared neutral core, not the adapter hook

The change
lands in `.pkit/permissions/decide.py` (`segments()` / classification), the
single neutral core both the hook and `pkit permissions` import. This preserves
the [ADR-002](ADR-002-permission-realizer-ownership.md) /
[ADR-003](ADR-003-permission-core-code-home.md) same-code invariant — one
`decide()`, identical decisions — and is covered by the existing conformance
fixtures.

### 5. The deny side remains porous

This ADR touches the deny side only by matching a deny on the words the shell
runs, in the forms below, and by abstaining where a pathname pattern or a
configuration assignment may make a command one a deny names (point 2). A deny
is matched on these forms of its command, as programs read them: a short flag
inside a bundle, a long flag cut to a prefix, carrying its value after `=` or
behind one dash, a program named by its path or in another case, and a
subcommand behind the options before it. Each reading errs toward the deny: a
prefix several long flags share reads as each of them. A grant is matched on
the command as written: reading these forms for a grant would widen what it
allows, while for a deny they only narrow what runs unasked. They are the
forms listed, not every form a command can take. A configuration git already
reads, or one an option such as `git -c` or a granted `git config` sets, stays
the grant's breadth, as `git -c core.fsmonitor=…` does (point 2). A program
behind a wrapper, such as `env`, is read as the wrapper: the core abstains where
no grant covers the wrapper, and a grant on a program runner allows what it
runs.
The deny side's mechanism — guardrail denies, the fail-open
hook + fail-closed native double-lock — is kept, and the merge layer / hook
remains a **speed-bump, not a boundary**
([ADR-004](ADR-004-autonomy-intent-confinement.md),
[ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md)). A reader must not
read a tighter allow path as a hardened deny path. Real confinement is still the
OS sandbox; real merge enforcement is still adopter-wired CI.

### 6. The broader widening is deferred per COR-007

A general
"auto-approve any compound whose every segment is independently safe" is **not**
taken (and is rejected outright as unsound — see Rationale). Any widening beyond
the leading-`cd` strip is gated on a *demonstrated residual-prompt need* — the
[COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md) recurrence
test, not speculative generality.

The removal of a redirection that writes no file (point 2) met that test, on
the evidence the Context gives for issue #2002.

## Rationale

**Why the leading-`cd` strip is safe.** `cd <path>`
changes nothing about *what* the remainder may invoke — it changes only the cwd,
which the intent layer already does not confine (a granted `gh pr list` is
granted regardless of cwd). Stripping it therefore reveals the intent that was
always there; it grants nothing new. It is the minimal, surgical reduction of a
false prompt, and it composes with the existing env-prefix strip the same way.

**Why a redirection that writes no file is safe to remove.** Duplicating an fd
onto stdout or stderr, closing one, or sending output to `/dev/null` changes
only where a program's output goes, never which program runs, and opens no
file. Output goes only where the command's own stdout or stderr already goes,
or nowhere.
Closing a stream may let a program's own output land in a file the program
opens itself, one its grant already lets it write. Removing the word reveals
the command a grant already covers, and a deny reads the same words. The care
is in the forms: `2>&1t` in zsh, or `>&word` with any other word, writes to a
file, `>&3` reaches whatever fd 3 the shell holds open, `{fd}>` sets a
variable, and in zsh a segment of redirections alone runs the program
`NULLCMD` names. So only the whole words point 2 names count, and every other
redirection stays untrusted. ADR-060 rejected reading shell writes into the
agent workspace, an allowlist of shell syntax whose holes all came from words
the shell expands. These forms are fixed literals that hold no character the
shell expands, so they carry none of those holes.

**Why "auto-approve any all-segments-safe compound" is rejected as unsound.** A
per-segment matcher sees pieces, not the whole. Safe pieces compose into unsafe
wholes the matcher cannot see: a redirection target turns a benign `echo` into a
file write (`echo x > ~/.ssh/authorized_keys`); `$(...)` and backticks smuggle a
second command inside a "safe" one; `| sh` pipes arbitrary text into a shell;
`find -exec` and `bash -c` carry a payload the segment matcher never inspects.
An all-segments-allowed rule would auto-approve every one of these. The
per-segment view is structurally blind to composition, so the general widening
is not merely deferred for sequencing — it is *unsound* and must not be built as
stated. (Surfaced by the `critic` pass.)

**Why no shell parser (altitude).** The hook is fail-open and runs under bare
`python3` inside Seatbelt (ADR-014). A shell parser is an adversarial-input
parser; hosting one in a fail-open, security-adjacent, dependency-constrained
component imports parsing fragility exactly where a parse bug becomes a silent
auto-allow. The dumb splitter's failure mode is the *safe* one — it abstains on
anything it does not understand. Keeping it dumb and pushing all conservatism
into "abstain when unsure" is the honest stance at this altitude. Reading one
segment's words by the quoting rules Python ships keeps that failure mode: a
quote that does not close, or any construct those rules read otherwise than the
shell, abstains.

**Why this is a refinement of ADR-004, not a supersession.** ADR-004's model —
intent × confinement, the double-lock, the speed-bump-not-boundary posture, and
decision point 4's fail-closed-on-uncertainty — is unchanged and is *inherited*
here. This ADR only refines how the intent axis classifies a Bash command: the
one shape of compound command it allows, the redirections it removes as writing
no file, and the words and forms a grant or a deny matches, while obeying
ADR-004's invariants. It adds no new ownership tier
and changes no prior decision.

### Alternatives considered

- **Auto-approve any compound whose every segment is independently safe.**
  Rejected as **unsound** (not merely deferred): a per-segment matcher is blind to
  composition. Redirection targets (`echo x > ~/.ssh/...`), `$(...)` / backticks,
  `| sh`, and `find -exec` / `bash -c` compose safe pieces into unsafe wholes the
  matcher cannot see, so the rule would auto-approve clear exfil/escalation. The
  leading-`cd` strip and the removal of a redirection that writes no file are
  sound at the per-segment view: neither changes which program runs or adds a
  file it writes.

- **A real shell parser in the decision core.** Rejected on altitude grounds —
  the hook runs bare `python3` in-sandbox (ADR-014) and is fail-open; an
  adversarial-input parser there trades a bounded, abstain-on-doubt splitter for
  parsing fragility in a security-adjacent component. The dumb splitter stays;
  conservatism lives in the classification.

- **Coaching-reject: bounce a compound back to the agent to re-issue as a single
  granted command** (enforcing core.md rule 15's "narrowest action" directly).
  Considered and **deferred** as a Phase-2 alternative. It has merit — it teaches
  the agent the narrow-action habit rather than silently accommodating compounds —
  but it changes the interaction shape (a reject-with-guidance, not a silent
  allow) and is gated on the same demonstrated-need test as the broader widening.

- **Implement the change in the adapter hook rather than the shared core.**
  Rejected — it would break the ADR-002 / ADR-003 same-code invariant, letting the
  hook and `pkit permissions` diverge on identical compounds. The change lands in
  the one neutral `decide()` both callers import.

## Implications

- **The change lands in `.pkit/permissions/decide.py`** (the `segments()` /
  classification path), the shared neutral core, and is covered by the existing
  conformance fixtures proving hook and CLI decide identically.

- **Deny mechanism kept; speed-bump posture preserved.** Guardrail denies,
  the fail-open hook + fail-closed native double-lock, and the
  speed-bump-not-boundary framing of ADR-004 / ADR-019 are unchanged. The deny
  side remains porous by design; this ADR narrows the allow path's false
  prompts and matches a deny on the words the shell runs, in the forms point 5
  names.

- **The broader widening is gated, not scheduled.** Any auto-approve beyond the
  leading-`cd` strip and the redirections that write no file requires a
  demonstrated residual-prompt need (COR-007), as point 6 records for the
  redirections. The all-segments-safe variant is recorded as unsound — a future
  author must not resurrect it as stated.

- **Supersedes nothing; child of ADR-004.** No prior decision changes. This ADR
  refines ADR-004's intent-axis classification and inherits its fail-closed,
  double-lock, and speed-bump invariants intact.

- **No migration.** The decision changes verdicts, never a file an installed
  project holds: no file/directory rename or removal in a kit-owned tree, no
  `schema_version` bump, no breaking CLI signature change, no capability-subtree
  restructure.

- **No version bump of the record's own.** Like the sibling permission ADRs,
  the record changes no component's surface: each change to the code that
  realizes it declares its own surface change.
