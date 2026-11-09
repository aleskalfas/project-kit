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
never allow, unless a deny binds on the words it reads (point 2).

A deny binds on the command and on the forms point 5 lists, such as a long
flag cut to a prefix. It also binds on what a listed runner runs, such as the
`rm` in `xargs rm -rf`. Where a pathname pattern, or git configuration the
command sets or writes, may make the command one a deny names, the core cannot
tell and abstains (points 2 and 5). Configuration git reads from its files
stays the grant's breadth.

Where the core cannot read what a runner runs, every deny may bind, and the
core abstains (point 5). Where a guardrail may hide, an adapter whose harness
has allow rules of its own asks the person, unless they chose not to be asked
(point 7). The code lives in the neutral core both the hook and the CLI import
(point 4).

**Decision in one line:** the core allows a Bash command only where a grant
covers every segment as written, after stripping one leading `cd` and each
redirection that writes no file. A deny binds on the command, on the forms
point 5 lists and on what a listed runner runs. Where git configuration the
command sets or writes may make it one a deny names, the core cannot tell and
abstains, and no doubt ever allows. A compound allowed because each segment
looks safe on its own is **rejected as unsound**, and any further
widening is **deferred** until a demonstrated residual-prompt need earns it
([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md),
point 6).

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

A third forcing question (issue #1990) is whether a deny reaches the command a
runner runs, or the configuration a command sets. Under the claude-code
adapter's baseline rule `Bash(find:*)`, `find . -exec rm -rf {} +` ran
unasked. Under `Bash(git:*)`, `git -c … push` ran unasked while
`GIT_CONFIG_PARAMETERS=… git push` prompted: one injection, two verdicts.

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
that writes no file are removed. Removing that `cd` and those redirections is a
prompt-reduction over already-granted intent, never a new grant. A rule blind
to how segments compose is rejected as unsound, and any other widening is
deferred.**

**A deny binds on the forms and through the runners point 5 lists. Where git
configuration the command sets or writes may make it one a deny names, the
core abstains. Every uncertainty fails closed (abstain / prompt), never to
auto-allow. Where a guardrail may hide, an adapter whose harness has allow
rules of its own asks the person, unless they chose not to be asked
(point 7).**

### 1. Phase 1 — strip a leading `cd`, decide on the remainder

When the first segment of a compound is a bare `cd <path>` (no quotes, no
substitution, no redirection but one that writes no file), the core drops it
and evaluates the remaining command against the grant model exactly as if it
had been issued alone. `cd src && gh pr list` with `gh pr list` granted
auto-approves, while `cd src && rm -rf /` does not (the remainder matches no
allow and, for guardrail denies, the deny still binds). The strip is one of
the two widenings this ADR makes. The other is point 2's removal of a
redirection that writes no file, which the core makes before it looks for the
`cd`.

### 2. Inherited fail-closed-on-uncertainty (ADR-004 decision point 4), non-negotiable

Any segment the core cannot read as the shell reads it makes the core
**abstain (prompt)**: an expansion opened by a `$` or a backtick, a
substitution opened by a `(`, a `<` / `>` redirection other than one that
writes no file (below), a word the shell splits, drops as a comment or
brace-expands otherwise than the core reads it, a leading assignment to a
variable that changes which program runs or loads code into it ahead of its
own, such as `PATH` or `LD_PRELOAD`, a leading assignment written with a quote
or a backslash, an operand of `export` other than a plain name or assignment,
which the shell expands before `export` reads it, a program name holding
whitespace, which a recognizer's pattern would read as two words, or an
unrecognized command. It NEVER auto-allows under uncertainty, and a deny on
the words it reads wins over any such construct. The core looks for such a construct in the whole command, a
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
program behind such a redirection. A form counts only as a whole word, or as
an operator and `/dev/null` with a space between, and only in a shape that
writes no file in bash, zsh or dash: each fd number is one digit or is left
out, the word after `>&` or `<&` is `1`, `2` or `-` alone, the target is
exactly `/dev/null` and unquoted, and `&>` or `&>>` stands last in its segment.
A removal never leaves a command of redirections and assignments alone, which
zsh runs as the program `NULLCMD` names: a segment so left, or left with only
a word that opens a command of its own, such as `{` or `do`, keeps the whole
command untrusted. The scan ignores quoting. Inside quotes such text is part of
an argument, and removing it changes only that argument's text, never a
program, a flag or a separator, since the whitespace around it stays. Any
other redirection, such as `>|`, `<>`, a here-string or a heredoc, stays
untrusted.

For a grant, outside an operand of `export`, a pathname pattern is matched as
written: it changes only arguments, from the names of files, never the program
a grant names. But such a pattern may expand to a word opening with `-`, an
option that may take the next word as its value. So where one stands before
the subcommand a grant names, or before the first of its flags the segment
holds, that grant does not allow the segment. A grant naming `docker ps` does
not allow `docker -* ps`, while a grant naming only the program matches a
pattern as written.

An assignment to a program's own setting, such as `GIT_PAGER`, is stripped
like any other: what a granted program is told to run is the grant's breadth,
as a pager set in git's configuration file is. Where an unquoted pathname
pattern, or an assignment that changes which configuration the program reads,
such as `HOME` or `GIT_CONFIG_GLOBAL`, may make the command one a deny names,
the core cannot tell, and abstains whatever a grant allows. It abstains rather
than denies, as on any other construct it cannot read: a deny would claim a
match the core cannot see. Such an assignment is still a program's own setting
to a grant. For a deny, it counts on every command of the program the deny
names, since the configuration may hold an alias of any name, and it counts
where the shell hands it on: for the command it stands in front of, and from a
segment that only assigns or exports, for the segments after it. The segment
splitter stays dumb: the conservatism lives in the classification, not in
parsing the shell's grammar.

### 3. No shell parser

The core keeps its dumb regex segmenter (`_SEP`). A real shell parser is
**rejected on altitude grounds**: the hook runs bare `python3` in-sandbox
([ADR-014](ADR-014-macos-sandbox-platform-stance.md)), and importing an
adversarial-input parser into a fail-open, security-adjacent component trades
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

The change lands in `.pkit/permissions/decide.py` (`segments()` /
classification), the single neutral core both the hook and `pkit permissions`
import. This preserves the
[ADR-002](ADR-002-permission-realizer-ownership.md) /
[ADR-003](ADR-003-permission-core-code-home.md) same-code invariant — one
`decide()`, identical decisions — and is covered by the existing conformance
fixtures.

### 5. The deny side remains porous

This ADR touches the deny side in two ways only. A deny is matched on the words
the shell runs, in the forms and through the runners below. Where the core
cannot tell whether a deny binds, it abstains (point 2). The permissions
README's section
["A deny holds against the forms of its command"](../../../.pkit/permissions/README.md#a-deny-holds-against-the-forms-of-its-command)
lists in full the forms, runners, git keys and cases this point names by
principle.

**Forms.** A deny is matched on these forms of its command, as programs read
them: a short flag inside a bundle, a long flag cut to a prefix, carrying its
value after `=` or behind one dash, a program named by its path or in another
case, and a subcommand behind the options before it. Each reading errs toward
the deny: a prefix several long flags share reads as each of them. They are the
forms listed, not every form a command can take.

**Runners.** A deny is matched on the command a runner runs, in every form
above, as well as on the runner itself. A runner here is a program that takes
another command as its own words, such as `xargs`, or find through `-exec`, and
the core reads that command as it reads any segment. A shell given `-c` is read
the same way, its script split and read again as a command, one level deep. A
program that takes code in a language of its own, such as `python3 -c`, is not
read.

The runners read are the set #1990 chose. So `xargs -0 rm -rf`,
`find . -exec rm -rf {} +` and `sh -c 'rm -rf ~'` are denied. A runner behind
a runner is read too, as in `env xargs rm -rf`. An assignment a runner makes,
as `env` does, counts as a leading assignment does (point 2).

**Where a runner cannot be read.** Where a word leaves the core unsure what a
runner runs, any program may run, so every deny of the subject may bind.
Examples are an option of the runner the core does not know, as in
`env -S '…'`, and a `-c` script holding `$1`. No grant then allows the command,
such as `find . -exec sh -c 'rm "$1"' _ {} \;`, and point 7 decides the core's
verdict on it. A deny the core reads for certain wins over this doubt.

**Configuration a command sets or writes.** Git configuration that can make a
git command another command or a forced push counts as part of the command,
where the command sets or writes it. An option before git's subcommand sets
it, such as `-c` or `--config-env`, and `git config` writes it, such as to an
`alias.*` or `remote.*.push` key. The options and keys are the set #1990 chose.
The core then cannot tell whether a deny on git binds, as after `HOME=…`
(point 2), and abstains.

A pathname pattern or a brace expansion counts as well where such an option or
key may stand, including before git's subcommand. So
`git -c alias.p='push --force' p`, `git config alias.pf 'push --force'` and
`git -* status` abstain. So does every `git -c`, such as
`git -c core.quotepath=off status`, a false prompt accepted until the PRJ-006
diagnostic log earns a list of safe keys. `GIT_CONFIG_PARAMETERS=… git push`
abstains through point 2's configuration assignment, so the two ways to inject
the same configuration get one verdict.

**Configuration git reads from its files.** Configuration git reads from its
files, such as a person's alias in `~/.gitconfig`, stays the grant's breadth.
Reading `.git/config` and the files it includes inside a fail-open hook is the
parsing fragility point 3 rejects.

**Grants.** A grant is matched on the command as written. A grant on a runner,
such as `uv-run`, allows the command the runner runs, where the core can read
that command and no deny binds or may bind on it. Reading these forms, or what
a runner runs, for a grant would widen what it allows, while for a deny they
only narrow what runs unasked.

**What stays unread.** Beyond the forms, runners and configuration above, the
core reads nothing, so these stay unread:

- a code runner, such as `python3 -c`
- git's own command runners, such as `git rebase --exec`,
  `git submodule foreach` or `git bisect run`
- arguments a runner reads from its input, as `xargs` does
- deletion by a program's own option, which no deny names, such as
  `find -delete`
- configuration written into git's files other than by `git config`, such as
  through the file tools, a shell write or `git remote add --mirror=push`
- an expansion in an argument, such as `git push origin $F`
- every command, while the hook is off

The deny side's mechanism — guardrail denies, the fail-open hook + fail-closed
native double-lock — is kept, and the merge layer / hook remains a
**speed-bump, not a boundary**
([ADR-004](ADR-004-autonomy-intent-confinement.md),
[ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md)). A reader must
not read a tighter allow path as a hardened deny path. Real confinement is
still the OS sandbox, and real merge enforcement is still adopter-wired CI.

### 6. The broader widening is deferred per COR-007

A general "auto-approve any compound whose every segment is independently
safe" is **not** taken (and is rejected outright as unsound — see Rationale).
Any widening beyond the leading-`cd` strip is gated on a *demonstrated
residual-prompt need* — the
[COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)
recurrence test, not speculative generality.

The removal of a redirection that writes no file (point 2) met that test, on
the evidence the Context gives for issue #2002.

### 7. The hook asks where a guardrail may hide

Where a deny may bind on what the core cannot see, the core abstains, or
denies under a strict posture, and names the subject's guardrails it cannot
rule out. A project's own deny on a privilege that is no guardrail is not
named, and is the speed-bump point 5 describes. An adapter whose harness has
allow rules of its own asks the person on such an abstain, since those rules
may run the command unasked. In a mode in which the person chose not to be
asked, such as Claude Code's auto and bypass modes, the adapter abstains, and
the harness's mode decides.

The core never reads the mode, so its verdicts are the same in every mode, as
[ADR-002](ADR-002-permission-realizer-ownership.md)'s same-code invariant
requires. Whether an adapter asks on such an abstain is this point's to
decide. How an adapter carries out any other abstain is its documentation's,
as ADR-002's Implications leave it. The Claude Code adapter's hook is the
realization.

## Rationale

**Why the leading-`cd` strip is safe.** `cd <path>` changes nothing about
*what* the remainder may invoke — it changes only the cwd, which the intent
layer already does not confine (a granted `gh pr list` is granted regardless
of cwd). Stripping it therefore reveals the intent that was always there, and
grants nothing new. It is the minimal, surgical reduction of a false prompt,
and it composes with the existing env-prefix strip the same way.

**Why a redirection that writes no file is safe to remove.** Duplicating an fd
onto stdout or stderr, closing one, or sending output to `/dev/null` changes
only where a program's output goes, never which program runs, and opens no
file. Output goes only where the command's own stdout or stderr already goes,
or nowhere. Closing a stream may let a program's own output land in a file the
program opens itself, one its grant already lets it write. Removing the word
reveals the command a grant already covers, and a deny reads the same words.
The care is in the forms: `2>&1t` in zsh, or `>&word` with any other word,
writes to a file, `>&3` reaches whatever fd 3 the shell holds open, `{fd}>`
sets a variable, and in zsh a segment of redirections alone runs the program
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
`find -exec` and `bash -c` carry a payload no grant reads. An
all-segments-allowed rule would auto-approve every one of these. The
per-segment view is structurally blind to composition, so the general widening
is not merely deferred for sequencing — it is *unsound* and must not be built
as stated. (Surfaced by the `critic` pass.)

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

**Why a deny reads what a runner runs, and a grant does not.** A runner hands
its words to another program, so a deny read on the runner alone misses the
program that runs. Under `Bash(find:*)`, a deny on `rm` read on `find` alone
would let `find . -exec rm -rf {} +` run unasked (#1990). For a deny, reading
what a runner runs only narrows what runs unasked. For a grant it would widen
what the grant allows, so a grant matches as written, as with point 5's forms.

**Why a listed set of runners.** The runners read are the set #1990 chose,
each a program that takes a command as its words. The core reads that command
with the splitter and word rules it uses for any segment, and a listed set can
be audited and tested. Other programs of that shape, such as git's own command
runners, stay unread, the porosity point 5 accepts. A code runner, such as
`python3 -c` or `awk`, takes code in a language of its own, which only a parser
per language could read, the fragility point 3 rejects.

**Why every guardrail may bind where a runner cannot be read.** A runner whose
command the core cannot read may run any program, so any deny may bind. Naming
only the denies on the runner would let `find . -exec sh -c 'rm "$1"' _ {} \;`
pass every guardrail under `Bash(find:*)`. Naming every guardrail fails closed
toward the person, who sees the command and decides, as ADR-004's fail-closed
stance asks. A deny the core reads for certain wins over the doubt, since doubt
never weakens a match.

**Why configuration a command sets or writes counts, and git's files do not.**
An alias or a push refspec that `git -c` or `git config` sets can make a git
command a forced push, whatever its words say. Such configuration stands in the
command's own words, as `GIT_CONFIG_PARAMETERS=…` does, so counting both gives
one injection one verdict. Configuration in git's files stands in no word of
the command, and `git config` writing such a key abstains. Reading those files
and their includes in the fail-open hook is the parsing fragility point 3
rejects.

**The cost.** Every `git -c` abstains, such as
`git -c core.quotepath=off status`, and so does a runner given an option the
core does not read. A find whose words hold an expansion or a brace, quoted or
not, is also a runner the core cannot read. Examples are
`find "$HOME/x" -name y` and `find . -name '*.{ts,tsx}'`, which the
claude-code adapter's baseline `Bash(find:*)` would run unasked, so the hook
asks.

Where the command is harmless, the person answers a false prompt. This ADR
accepts these prompts until the PRJ-006 diagnostic log shows which recur. That
evidence may then earn a list of safe keys or options, under COR-007.

**Why the hook asks where a guardrail may hide, unless the person chose not to
be asked.** An abstain hands the call to the harness, whose own rules, such as
`Bash(git:*)`, may run a hidden forced push unasked. So where the core names a
guardrail it cannot rule out, the adapter asks, and the person who sees the
command decides. In a mode in which the person chose not to be asked, such as
Claude Code's auto or bypass mode, the adapter abstains and the mode decides.
The core reads no mode, so the hook and the CLI decide alike (ADR-002).

**Why this is a refinement of ADR-004, not a supersession.** ADR-004's model —
intent × confinement, the double-lock, the speed-bump-not-boundary posture, and
decision point 4's fail-closed-on-uncertainty — is unchanged and is *inherited*
here. This ADR only refines how the intent axis classifies a Bash command: the
one shape of compound command it allows, the redirections it removes as writing
no file, the words, forms and runners a grant or a deny matches, and where an
adapter asks on the core's doubt, while obeying ADR-004's invariants. It adds
no new ownership tier and changes no prior decision.

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

- **Match a deny on the runner alone.** Rejected: a deny on `rm` then misses
  `xargs rm -rf` and `find . -exec rm -rf {} +`, which a harness rule such as
  `Bash(find:*)` runs unasked (#1990). The guardrails would guard only a
  command written plainly. Reading what a listed runner runs narrows what runs
  unasked and widens no grant.

- **Read git's configuration files.** Rejected: telling whether an alias in
  `~/.gitconfig` or `.git/config` hides a forced push means reading those files
  and their includes inside the fail-open hook. That is the parsing fragility
  point 3 rejects. Configuration a command sets or writes is read instead,
  since it stands in the command's own words.

## Implications

- **The change lands in `.pkit/permissions/decide.py`** (the `segments()` /
  classification path), the shared neutral core, and is covered by the existing
  conformance fixtures proving hook and CLI decide identically. A deny's reading
  of a runner's command, and of the configuration a command sets or writes,
  lives there too.

- **Deny mechanism kept; speed-bump posture preserved.** Guardrail denies,
  the fail-open hook + fail-closed native double-lock, and the
  speed-bump-not-boundary framing of ADR-004 / ADR-019 are unchanged. The deny
  side remains porous by design; this ADR narrows the allow path's false
  prompts and matches a deny on the words the shell runs, in the forms and
  through the runners point 5 names.

- **The hook's ask is point 7's.** Whether an adapter asks on the core's doubt
  about a guardrail is decided here, and the core's verdicts are the same in
  every mode. The adapter's documentation describes how its hook carries the
  ask out.

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
