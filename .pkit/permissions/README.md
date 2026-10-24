---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/permissions/*.py
        - .pkit/permissions/profiles/**
        - .pkit/schemas/privilege-catalog.yaml
        - .pkit/schemas/privilege-catalog.schema.json
        - .pkit/adapters/claude-code/permission-hook.py
        - .pkit/adapters/claude-code/settings/core/settings.json
        - src/project_kit/permissions.py
        - src/project_kit/workspace.py
        - src/project_kit/run_rules.py
        - .pkit/schemas/permission-runs.schema.json
      record: [COR-028, PRJ-006, ADR-002, ADR-003, ADR-004, ADR-009, ADR-014, ADR-016, ADR-021, ADR-025, ADR-060, ADR-066]
      artefact: [.pkit/cli/README.md#agents-rules-capabilitycommand---agent-agent---json, .pkit/adapters/claude-code/README.md#live-permission-enforcement-permission-hookpy]
    revalidated:
      at: 2026-10-24T10:54:20Z
      outcome: updated
---

# Permissions — decision core

Propagated, harness-neutral code home for the permission **decision core** (per [COR-028](../decisions/core/COR-028-permission-model-realization.md) and [ADR-003](../../tech-docs/architecture/decisions/ADR-003-permission-core-code-home.md)).

This is **not** a COR-011 area — it has no content layout of its own. It is a propagated code directory (synced into adopters via `PROPAGATED_AREAS`, like `adapters/`), holding the logic that both consumers import so they decide identically (ADR-002's same-code invariant):

- the `pkit permissions` CLI (`explain` / `diff`), running in the global runtime, and
- the claude-code PreToolUse hook, running in the adopter tree at decision time (where the global `pkit` is not importable).

**Dependency direction (ADR-003):** the CLI and the hook import this; this imports neither `src/project_kit` nor any adapter. Recognizers arrive as catalog *data* (`../schemas/privilege-catalog.yaml`), never as adapter code.

- `decide.py` — `decide(model, catalog, request, posture) → allow|deny|abstain` + the recognizer matcher + the path-scoped allow behind the agent workspace (see "The agent workspace") + `hook_decide()` (fail-open) + `hidden_guardrails()` / `hook_hidden_guardrails()` (the guardrails a deferred Bash command may hide, which an adapter may ask the person about, as "A deny holds against the forms of its command" says) + the **single model loader** `load_catalog()` / `load_model()` (both the hook and the CLI build the model through these, so they decide identically; `load_catalog()` also merges installed capabilities' privilege-catalog fragments per ADR-021 — additive-only, collision-rejecting, guardrail-forbidding) + `guardrail_denies()` (synthesizes the baseline `all`/`deny` grants from the privileges the catalog flags `guardrail: true` — the model half of ADR-002's double-lock). Also contains `_stdlib_load_yaml()` — a stdlib-only YAML-subset fallback invoked by `load_yaml()` when `ruamel.yaml` is not importable (e.g. inside macOS Seatbelt where `uv` panics, per ADR-014). **The fallback lives here, in the shared loader, not in the hook** — so the hook and CLI parse via the same code path (ADR-002/ADR-003 same-code invariant). Conformance fixtures live at `tests/test_permission_decide.py` (including parse-equality tests between ruamel and the stdlib fallback on all shipped files); the hook's end-to-end tests at `tests/test_permission_hook.py`.

- `diagnose_capture.py` — the harness-side **capture** half of the permission-prompt diagnostic loop (per [PRJ-006](../decisions/project/PRJ-006-permission-prompt-diagnostics.md)). Propagated beside `decide.py` and imported by the PreToolUse hook *after* the decision is computed. It is deliberately **separate from `decide.py`** so the decision core stays pure: `capture()` is a side-effect (a "prompt" is a harness behaviour), gated on the deferred (`abstain`) verdict, active only while a TTL-bounded session is armed, and **inert on any failure** — its own internal `try` (plus the hook's outer `try`) guarantees a capture fault can never change a decision or break fail-open. Stdlib-only, same bare-`python3` runtime constraint as `decide.py` (ADR-014). End-to-end tests at `tests/test_permission_hook.py`; unit + redaction/size-cap/inert tests at `tests/test_permission_diagnose.py`.

## The permission-prompt diagnostic loop (PRJ-006)

An opt-in, **recommend-only** loop that turns confirmation-prompt friction into a measurable, closable feedback loop. Two halves, split along the [ADR-002](../../tech-docs/architecture/decisions/ADR-002-permission-realizer-ownership.md) same-code / harness-boundary seam:

- **Capture** (harness side, `diagnose_capture.py`, above): while *off* (the default), the hook does one cheap marker read and logs nothing; while *armed*, it appends each deferred decision to a local log. Because the hook observes only its own deferral — not whether the harness ultimately prompted — the captured signal is a **superset** of real prompts; the report states **coverage**, never a predicted prompt-count decrement.
- **Arm / disarm / classify / report** (CLI side, `src/project_kit/permissions.py`, the `diagnose_*` functions): `pkit permissions diagnose on | off | status | report`. The armed marker (`project/diagnose.yaml`) carries a **TTL** so a session auto-expires and can't stay silently on; the log (`project/diagnose-log.jsonl`) is size-capped (drop-oldest), command-tail-redacted by default, and **git-ignored** (both files, via the pkit-owned `.pkit/.gitignore` render — their paths are contributed to the aggregated `runtime_ignore` set and rendered wholesale, per ADR-009 rule 7). The classifier groups raw command text into a taxonomy that lives **in code, not in the record** (it churns as it meets real data) and is **advisory for ranking only** — it orders + explains the report but never authorizes a change. The MVP **applies nothing**: auto-fix is deferred, and authoring a new catalog privilege is never auto-fixable.

### Two sharpening axes on the report (issue #317)

The capture is a *superset* (the hook sees its own abstain, not the harness's final answer), so the report adds two **static** axes — computed over the logged (redacted) command text, no capture-format change — that turn raw deferral counts into actionable ones. Both reuse the existing settings readers (`_live_settings` / `_read_settings_local`), the `_BASH_RULE` parser, and the canonical shell-operator splitter (`decide.segments`); no new matcher is introduced. Both stay **recommend-only** — the report still applies nothing.

- **prompted vs auto-allowed.** A captured record is an abstain the *hook* deferred on; the harness then applies the live `settings.json` (+ `settings.local.json`) `permissions.allow` patterns. The report flat-matches each record against them — a bash command whose leading tokens are exactly a `Bash(<prefix>:*)` pattern, or a non-bash tool call (`Read`, `Edit`, …) whose tool is allow-listed — and reports **real prompts** (no match) separately from the **auto-allowed superset** (`N real prompt(s) of M captured (M−N auto-allowed by settings.json)`). A shell-shape command (`&&`, `|`, `;`, `$(…)`, …) is never auto-allowed by the single-pattern flat matcher, so it always lands as a real prompt.
- **allowlisted-but-compound vs genuinely-missing.** Of the *real* prompts, the report decomposes each command on shell operators and tests every non-`cd` segment (a bare `cd <path>` is a cwd change, never an intent target — [ADR-025](../../tech-docs/architecture/decisions/ADR-025-segment-conservative-bash-allow.md)) against the same matcher. **Allowlisted-but-compound** = shell-shape and every segment individually allow-matched — an allowlisted command defeated *only* by compounding, i.e. a decomposition / butter-verb target the report recommends eliminating at source. **Genuinely-missing** = a real allowlist gap (an uncovered segment head, a bare uncovered command, or an un-allowed tool). The headline carries the split; the shell-shape group line is tagged with it.
- **Scope / honesty.** Both axes are static over redacted text, so they inherit the redaction's kept-head limit (a `Bash(<prefix>:*)` longer than the preserved head can't prefix-match) and read `deny` patterns out of scope (logged records already abstained, so a guardrail deny is decided upstream, not here). The numbers sharpen the superset honesty; they do not promise a live prompt-count decrement.

### A prompt for the agent workspace is a defect

The capture half tags each deferral with `workspace: true|false` — whether the decision core's own recognizer (below, "The agent workspace") places a file tool's target in the workspace; the path itself is never logged. The report puts every tagged deferral in a `workspace` group under its own **DEFECTS** band, ahead of every recommendation: the workspace is granted to every agent, so a file-tool prompt there is never an allowlist gap to tune around but a missing active profile or enforcement that is off — worth a report, not a new allow rule. A shell command writing into the folder is not tagged: it is judged like any other shell write, so its prompt is an ordinary one.

## The agent workspace

Every checkout of a project has one **agent workspace**: `.agent-workspace/` at its root, where agents keep their intermediate files — pull-request and issue bodies, scripts, captured output, notes — and nowhere else outside the repository (`rules/core.md`, the workspace rule; [#1043](https://github.com/aleskalfas/project-kit/issues/1043)). The design — a path-scoped allow, recognised from a file tool's target path, with no shell exception — is [ADR-060](../../tech-docs/architecture/decisions/ADR-060-path-scoped-workspace-allow.md). This is the contract every harness adapter meets:

- **Per checkout, never committed.** `pkit init` and `pkit sync` create the folder and exclude it through the repository's local exclude file in the common git directory: each worktree has its own folder at its own root, one exclude entry covers all of them, and nothing in them reaches a commit. That entry covers the clone it was written in; `init` recommends the same line for the project's committed `.gitignore`, which covers every clone and which pkit never writes itself (CLI reference, `init` step 4). Nothing in the folder is shared between clones.
- **Granted to every agent, for the file tools, and only there.** The catalog's `workspace` privilege is a **path-scoped allow** (`recognize.path`): it is recognized only for a file tool the privilege lists (`Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`) whose *target* lies inside `.agent-workspace/` of the project root or of another working tree of the same repository — never for the tool alone. It reduces prompts on the allow side, keyed on the target path; it confines nothing — shell reach is the OS sandbox's, and for the file tools, which run outside the sandbox, the recogniser's precision is the gate inside the folder (ADR-060 point 6). A grant of it can therefore neither reach nor deny a file anywhere else; outside the folder the privilege does not apply and a request is decided exactly as before. Every shipped profile grants it to `all`, `read-only` included — the folder holds nothing a commit can carry.
- **What lies inside.** A target whose path resolves inside the folder, symlinks resolved — a link out of the folder is outside. The folder counts only as the checkout itself holds it: a symlinked `.agent-workspace` is never the workspace, a catalog folder entry that is absolute or climbs out with `..` is never recognized, and another working tree counts only when git registered it for the same repository — another repository's workspace never does. A repository or worktree nested inside the folder is not the folder: when any directory from the folder down to the target holds a `.git` entry, the target is another checkout's. Nor is an existing file with more than one link — a hard link planted in the folder would carry a write to its other name.
- **No shell command is the workspace's.** A redirect, a here-document or an `rm` into the folder is judged like any other shell write, the leading-`cd` strip included (below): a remainder with a redirect still abstains. Write intermediate files with the file tools.
- **Realized by the hook, never as a session-wide rule.** The projection reports a `workspace` grant as `runtime`, not as a native allow: a harness-wide `Write` or `Edit` rule would reach far beyond the folder. An adapter whose harness does not already approve the folder emits the narrowest path-scoped rule its harness offers; one whose harness does emits nothing — the Claude Code adapter's README says which it is, and its enforcement declaration names the dimension `path-scoped-allow`.
- **A prompt there is a defect** — see the diagnostic loop above.

## Scope enforcement

Grant scope globs constrain the reach of an allow grant. The dimension matched depends on the privilege's `scope_type` in `privilege-catalog.yaml`:

- **`directory` scope** (e.g. `docker`): grant scope globs are matched against the request's `cwd` via `fnmatch`. A request outside the listed paths is denied. This is enforced by the hook at decision time; it is not an OS-level confinement boundary (see ADR-004 for why shell confinement via cwd checking is not a security boundary).

- **`domain` scope** (e.g. `web-fetch`): grant scope globs are matched against the **hostname** of the request URL via `fnmatch` — **positive allow-list semantics**. The grant permits only URLs whose host matches at least one glob. A request with a non-matching host, or a request missing a parseable URL, is denied.

  Example grant (in `project/grants.yaml`):

  ```yaml
  - subject: agent:researcher
    privilege: "[privilege-catalog:web-fetch]"
    scope: ["docs.python.org", "*.github.com"]
    effect: allow
  ```

  This allows `researcher` to fetch from `docs.python.org` or any subdomain of `github.com`, and blocks all other hosts.

- **No scope** (absent): the grant is unconstrained — any cwd / any host.

A scope *confines* a privilege: a scoped allow denies the privilege outside its scope. The agent workspace needs the opposite — a privilege that exists only inside a folder and has no opinion elsewhere — so its folder is part of the privilege's recognizer (`recognize.path`), not a grant scope; see "The agent workspace" above.

## Compound commands (segment splitting + leading-`cd` strip)

A compound Bash command reaches `decide()` as one string. The decision core splits it on `&&` / `||` / `|` / `;`, a background `&` and a newline with a **dumb regex segmenter** (no shell parser — see ADR-025 for the altitude rationale: the hook runs bare `python3` in-sandbox, where hosting an adversarial-input parser would trade an abstain-on-doubt splitter for parsing fragility) and decides on the per-segment matches. Within each segment it reads the words as the shell does: it splits them at spaces and tabs, and removes quotes and backslashes by the standard library's POSIX quoting rules. So a grant or a deny matches `"--force"` as `--force`, and `git commit -m "fix: x"` as the command the shell runs. That reads words, never the shell's grammar, so it is no shell parser. Two prefix-strips reduce false prompts over already-granted intent:

- **Env-prefix strip** (`segments()`): a leading `export` / `VAR=value` on a segment is dropped before matching, so `export GH_HOST=x && gh pr list` matches `gh pr list`. An assignment counts only where its name is written unquoted, as the shell reads it. A segment that only assigns, with an untrusted construct (below) in it, such as `X=$(./x.sh)`, is not dropped. Its value may run a command, so the segment stays, and no grant covers it.

- **Leading-`cd` strip** (ADR-025 Phase 1): when the **first** segment is a bare `cd <path>` followed by `&&` / `;`, the core drops it and decides on the remainder against the unchanged grant model — `cd src && gh pr list` auto-approves exactly as `gh pr list` would. It is a prompt-reduction over already-granted intent, **never a new grant** (`cd` only changes the cwd, which the intent layer does not confine), and the remainder is decided at the **original** cwd (the strip can never grant a directory-scoped privilege the un-stripped command lacked).

  The strip is deliberately conservative, and fails closed (ADR-004 decision point 4):

  - **Only a bare `cd`** is stripped — a single path arg, parted from `cd` by a space or a tab, no quotes, no `$()`, no backtick, no redirection, no flags. A `cd "/x; rm -rf ~" && …` is *not* a bare `cd`, so it is not stripped and falls through to the full-command path, where its deny still binds. Deny-wins is never weakened.

  - **No `cd` is stripped from a command holding an untrusted construct, a word the core cannot read as the shell does, or such a leading assignment** (all below), its `cd` included. Such a command is decided whole, so `cd {a,b} && git status` never hides what its `cd` word runs.

  - **The remainder is decided like any command.** An untrusted construct in it keeps every grant from allowing it, as it does anywhere in a command (below). So `cd /x && echo z > ~/f` and `cd /x && gh $(rm -rf ~)` prompt rather than slip through — and so does a redirect into the agent workspace (`cd /x && cat > .agent-workspace/body.md <<'EOF'`): the workspace grant covers the file tools only.

  - **A pipe is decided segment by segment.** The cd-strip does not touch pipes, and `|` is not a cd-separator. So `cd /x && gh … | sh` decides exactly as the bare `gh … | sh` does, and both abstain, since every segment needs its own allow (below).

  The broader "auto-approve any compound whose every segment is independently safe" widening is **rejected as unsound** (a per-segment matcher is blind to composition), and any other widening is deferred per COR-007 — the leading-`cd` strip is the only widening taken. See ADR-025.

**Every segment needs its own allow** (ADR-025 point 2). The core allows a compound only when an allow grant covers each segment the splitter yields. A segment that matches no privilege, or only privileges no allow grant of the subject reaches, makes the core abstain. The call then goes to the harness's own flow, and a strict posture denies it instead.

So where only `gh` is granted, `gh pr list | sh` and `gh pr list & python3 x.py` abstain, as does `python3 x.py` on the line after `gh pr list`. So does a pipe into a filter no grant covers, such as `gh pr list | jq .`. A compound whose every segment is granted, such as `git diff | git apply --check`, is allowed. That is not the widening rejected above: each segment needs a grant of its own, never a judgement that it is safe.

**The read-only filters and the Python runner** ([#2000](https://github.com/aleskalfas/project-kit/issues/2000)). Two catalog privileges cover the programs a compound most often pipes into or runs. A compound of them and other granted programs is then allowed, each segment still on a grant of its own:

- **`read-filter`** recognizes programs that read files or standard input, write only to standard output and run no other program. These are `cat`, `head`, `tail`, `wc`, `cut`, `tr`, `grep`, `egrep`, `fgrep`, `jq`, `ls`, `cmp`, `basename`, `dirname`, `realpath`, `pwd`, `echo`, `true` and `false`. It also recognizes `sort` with no word opening an output file, a compress program or a temporary directory, and `uniq` with no second operand. Every shipped profile grants it to `all`
- **`python-runner`** recognizes `uv`. `uv run` runs whatever program it is given, so a grant allows what that program does. A guardrail's deny does not see past `uv` to that program. No shipped profile grants it (ADR-005), so a project grants it in its own `grants.yaml`, as project-kit does

Neither recognizes a program that writes a file or runs another, such as `sed`, `awk`, `find`, `xargs`, `tee` or `rg`. Nor does either recognize `diff`, whose `-l` runs `pr`, or `printf`, since the shell's `printf -v` sets a variable such as `PATH`. So under a shipped profile, `grep x f | head` is allowed for every agent, and `grep x f | sed s/a/b/` defers.

**An untrusted construct keeps every grant from allowing** (ADR-025 point 2). Where a Bash command holds a construct the dumb splitter cannot be trusted on, its segments may not be the commands the shell runs. These are a backtick, a `<` / `>` redirection, and a `(`, which opens every substitution: `$(…)`, `<(…)` / `>(…)`, zsh's `=(…)`, and zsh's glob qualifiers and parameter flags that run code. A `$` is one too, since it opens every expansion. Its value is one the core never sees, and some forms, such as `${X@P}` and `$[…]`, evaluate it as code. The scan finds each of them inside quotes as well. Such a command, with or without a leading `cd`, makes the core abstain, and a strict posture denies it instead.

**So does a word the core cannot read as the shell does** (ADR-025 point 2). Its words may not be the words the shell passes on:

- a quote or a backslash that does not close, as where the splitter cuts a quoted `;`
- whitespace other than a space, a tab or a newline, such as a no-break space, inside which the shell reads one word
- a word opening with `#`, a comment the shell drops
- a brace expansion, such as `{a,b}` or `{1..3}`, which the shell turns into several words
- a program name holding whitespace, such as `'make test/x'`, which a recognizer's `pattern` would read as two words

**And so does a leading assignment that changes which program runs, or one written with a quote or a backslash** (ADR-025 point 2). `PATH=/tmp/x gh pr list` runs whichever `gh` the new path finds first. Each such assignment is stripped for the denies, so `PATH=/tmp/x sudo id` is denied.

- **The variables that change which program runs** are a search path, `PATH` or any other name ending in `PATH`, and the dynamic loader's `LD_*` and `DYLD_*`. So are the variables that name the startup files a shell reads first, such as `BASH_ENV`, `ENV` and `ZDOTDIR`, and the options of Python, Perl, Ruby, Node and Java, which load code ahead of the program's own. The list names a family of variables, and is no boundary.
- **A program's own setting,** such as `GIT_PAGER=cat`, is stripped and allowed: what a granted program is told to run is the grant's breadth. A `git` grant already lets `git -c core.fsmonitor=…` run any program. A setting that changes which configuration the program reads may still keep a deny from telling (below).
- **An assignment written with a quote or a backslash** is never allowed by a grant. The core never matches an assignment's value, so removing its quotes would make no match more accurate: only a quoted argument is matched as the shell passes it on.

A segment led by `export` runs no program: `export` takes each word after it as a name or an assignment, so `export git PATH=/tmp/x` sets `PATH` and runs no `git`. Its assignments are judged as above, and no grant on a program covers it. Each word after `export` must be a plain name or assignment: the shell expands any other first, so `export PAT?=bin` sets `PATH` where a file named `PATH=bin` lies in the directory, and such a word keeps every grant from allowing. A segment led by `builtin export` or `command export` stays a program no grant covers.

So where `gh` and `git` are granted, `gh pr list > ~/.bashrc`, `gh pr list $(python3 x.py)` and `PATH=/tmp/x gh pr list` abstain, and the harness's own flow decides each. A quoted argument alone is none of these: `git commit -m "fix: x"` is allowed, and `git push origin main "--force"` is denied as `--force` is. For a grant, outside an `export`, a glob is read as written: it changes only arguments, from the names of files, never the program a grant names.

A deny on any segment still wins over every allow, and over an untrusted construct. The abstain's reason names each uncovered segment's program where that is a bare word, and never its arguments, so it undoes none of the diagnostic log's redaction. The reason for an untrusted construct lists the kinds of construct, and none of the command's text.

## A deny holds against the forms of its command

A grant matches a command as it is written. A deny, a guardrail's included, also matches these forms of it, as programs read them (ADR-025 point 5):

- a short flag inside a bundle, such as `-f` in `git push -uf`
- a long flag cut to a prefix, such as `--force-w`, which git reads as `--force-with-lease`
- a long flag with its value after `=`, such as `--force-with-lease=main`, or behind one dash, such as `-force`
- a program named by its path, such as `/usr/bin/sudo`, by zsh's `=sudo`, or in another case, such as `Git`, which macOS runs as `git`
- a subcommand behind the options before it, such as `push` in `git -C . push --force`

The core reads these forms from a structured recognizer's `cmd`, `subcommand` and `flag_any`. Each reading errs toward the deny: a prefix several long flags share reads as each, and so does an option that is itself a prefix of a denied one, such as `--proxy` of `--proxy-insecure`.

A recognizer's regex `pattern` is matched with a program's path cut to its name, and with the options before a subcommand left out. The core reads up to 64 places where the subcommand may stand behind an option's value, and past them it defers. Otherwise the regex is matched as written, so it spells each form of the flags it names, as the shipped `destructive-fs` regex spells `--recursive` cut down to `--r`.

The `vcs-history-rewrite` guardrail also names `--mirror`, which force-updates every ref the remote holds. It names a refspec opening with `+`, as in `git push origin +main`, through the recognizer field `word_prefix_any`.

**Where a deny may bind on what the core cannot see, no grant allows the command.** The core then defers, naming the deny, and a strict posture denies. Two things keep it from seeing:

- **A pathname pattern**, such as `--forc[e]` or `*`, which the shell expands to the names of files. A glob character counts outside quotes alone, so `git push origin '[+]main'` is read as written. For a structured recognizer, the core cannot tell where such a pattern stands for the program or the subcommand, or may open with `-` or `+`. For a regex `pattern`, it cannot tell where one stands anywhere in a segment of the program the regex opens with, or of any program where it opens with none plainly.
- **An assignment that changes the program's configuration**, which may set a forced refspec or an alias. These are `HOME`, the XDG base directories, any name holding `CONFIG`, such as `GIT_CONFIG_GLOBAL`, and git's repository directories. Such an assignment counts in front of a command, for that command, and in a segment that only assigns or exports, `builtin export` included, for the segments after it. It keeps a deny from telling on any segment of the program the deny names, so `HOME=/tmp/x git status` defers.

**Where Claude Code may allow what the core defers on a guardrail, the person is asked.** A harness's own rules may allow a command the core defers, as Claude Code's baseline allows `git push origin --forc[e]` by `Bash(git:*)`. So the core names each guardrail among the subject's denies that may bind on a deferred command in a form it cannot see (`hidden_guardrails()`). An adapter may use it to ask the person rather than defer.

The Claude Code hook asks the person on such a command ([the adapter's README, "Live permission enforcement"](../adapters/claude-code/README.md#live-permission-enforcement-permission-hookpy)). A project's own deny, such as the project manager's on raw `gh` mutations, is no guardrail, so the core names none for it, and where it cannot tell the deny it defers. The deny side stays a speed bump all the same (ADR-025 point 5).

What the forms leave out stays unseen, and nothing asks about it. A git alias or refspec set in a configuration git already reads, or through `git -c` or a granted `git config`, is the grant's breadth (ADR-025 point 5). A program behind a wrapper, such as `env` or `command`, is read as the wrapper. No shipped grant covers one, so the core defers, but a project's grant on a program runner, such as `xargs`, would allow what it runs.

A command the core defers for a construct it cannot read, such as `git push origin $F`, names no guardrail either, so the harness's own rules decide it. So does a wrapper the harness allows, as Claude Code's baseline allows `find`, and with it `find . -exec rm -rf {} +`, which no native deny's prefix matches.

## Default-agent subject resolution

The hook resolves the subject for every PreToolUse call.  Subject resolution
order (per issue #57):

1. **`agent_type` present in the payload** → `agent:<agent_type>`.  Claude Code
   sets this for spawned Task-subagents; the result is unchanged.

2. **`agent_type` absent + `.claude/settings.json` has `agent: X`** →
   `agent:X`.  The main session runs *as* that agent — all per-agent grants
   (allow and deny) apply.  `settings.json` is read with stdlib `json`; a
   missing, unreadable, or malformed file silently falls back to rule 3.

3. **`agent_type` absent + no `agent` key in `settings.json`** → `operator`.

**Implication:** in a session with a configured default agent, a human's
`!`-typed command is also bound to that agent's grants — consistent, because the
session runs *as* the agent.

**A session started with `--agent`.** The review command's runs name their
agent on the command line, through the agent runner ([the adapters README, "The
agent runner"](../adapters/README.md#the-agent-runner)). That sets the session's agent without changing
`.claude/settings.json`, the file rule 2 reads. A confined run, such as a
fixer's, loads no project settings, so the hook is not registered there at all
("The rules of an agent run" below). So the hook may judge such a
run as the project's default agent, or as `operator`, rather than as the agent
it names. No grant for one agent counts in those runs until the probe shows
which subject the hook judges
([ADR-066](../../tech-docs/architecture/decisions/ADR-066-unattended-agent-runner.md)
point 11).

Without this resolution (the pre-#57 behaviour), the main session always resolved
to `operator` even when `settings.json` set `agent: project-manager`, making
every per-agent grant inert for the primary execution context.

## Surgical deny: blocking raw gh mutations for project-manager

The `issue-tracker-write` privilege (in `privilege-catalog.yaml`) recognizes
the three raw `gh` mutations that bypass the project-management capability's
validating scripts:

- `gh issue edit`
- `gh issue comment`
- `gh pr edit`

It does **not** match `gh issue view`, `gh pr view`, `gh api`, or any other `gh`
subcommand — only mutations.

A companion privilege, `issue-tracker-read-raw`, recognizes the three raw read
**views** the project-management capability's clean-output verbs replace:

- `gh issue view`
- `gh pr view`
- `gh pr diff`

It is denied for `project-manager` by the same capability fragment, routing the
agent to `pkit project-management show-issue` / `show-pr` (and their `--field
<name>` for a single value) — the prompt-free, non-piping read path. The
recognizer is deliberately narrow: it matches **only** those three views, never
`gh pr checks`, `gh run`, `gh api`, `gh issue list`, or `gh pr list`, and never a
mutation (those are covered by `issue-tracker-write` or left open). A deny is
auto-rejected by the harness (no operator prompt), so the agent adapts to the
clean verb.

### Where the deny lives (ADR-016)

The deny is a **capability-contributed grant** shipped by the project-management
capability at `.pkit/capabilities/project-management/permissions/grants.yaml`.
It is **not** a manual grant in `project/grants.yaml` (which stays empty for this
policy). `load_model` discovers it by walking the manifest `components:` list;
a capability directory not registered in the manifest contributes nothing
(install-state-as-gate). Run `pkit permissions overview` to see it listed under
"CAPABILITY-CONTRIBUTED DENIES".

When project-manager calls `gh issue edit`, the request matches **two** privileges:

- `issue-tracker` (the broad `cmd: gh` recognizer) — **allowed** (once
  `issue-tracker` is granted to the agent via the active profile)
- `issue-tracker-write` (the mutation pattern) — **denied** by the capability fragment

`decide()` provides order-independent deny-wins semantics: it continues
iterating all effective grants after setting `matched_allow = True` for an
allow grant, and short-circuits immediately on any deny-overlap hit — so the
explicit deny wins regardless of grant ordering, even when the `autonomous`
profile grants `issue-tracker` to all.  No change to `decide.py` was required;
the existing loop already guarantees this property.

The capability scripts' internal `gh` calls are **unaffected**: they run inside
the `pkit` subprocess, below the PreToolUse hook layer — they are not Claude
Code tool calls and are therefore not subject to hook-based enforcement.

## Capability-contributed privilege *definitions* (ADR-021)

ADR-016 (above) lets a capability ship its own deny *policy*, but the privilege
the deny references still had to be *defined* in the backbone catalog. ADR-021
closes that gap: an installed capability may also ship a **privilege-catalog
fragment** at `.pkit/capabilities/<cap>/permissions/privilege-catalog.yaml`,
which `load_catalog` merges into the central catalog. A capability now ships a
privilege **definition and** its deny together, self-contained, with no
core-catalog edit (which `pkit sync` would overwrite anyway).

The fragment reuses the existing `privilege-catalog.yaml` document shape — **no
new schema**. Discovery is install-gated like the grants walk: only
manifest-registered capabilities contribute (an orphan directory contributes
nothing). The merge rule — **additive-only, collision-rejecting,
guardrail-forbidding**, with each fragment id rewritten to a capability-scoped
`<cap>:<name>` key — is ADR-021's; read it for the full semantics and the safety
rationale. In short: a fragment can extend the recognised *vocabulary* in its own
namespace but can never overwrite a backbone or peer privilege, and can never
install a deny on every adopter (a `guardrail: true` fragment entry is rejected).
A grant references a scoped privilege with the COR-019 token whose id half carries
the scope (`[privilege-catalog:<cap>:<name>]`, per COR-019's id-scope
clarification).

`pkit permissions overview` attributes each merged privilege to its contributing
capability and surfaces any rejected fragment. A fragment privilege is **inert**
until a grant references it; the narrowing is the deny grant the capability also
ships (ADR-016's channel, unchanged), and a tool-call deny is a behaviour-shaping
speed-bump, **not** a security boundary (ADR-004).

### Authoring a fragment (`pkit permissions scaffold <cap>`)

Both fragment files are hand-authored and kit-owned. To stamp the skeleton with
the correct shapes and inline footgun guidance, run `pkit permissions scaffold
<cap>` (paired with the `capability-author` skill, step 6b). It stamps
`privilege-catalog.yaml` + `grants.yaml` into the capability's `permissions/`
dir, refuses an unknown capability, and refuses to clobber an existing fragment.

Two footguns the scaffold guidance captures: a fragment privilege key is authored
**bare** (the loader applies the `<cap>:` scope), and a grant references it with
the **scoped** token `[privilege-catalog:<cap>:<name>]`. A *bare* grant token
against a fragment privilege resolves to no merged privilege, so the deny
silently does **not** bind — the fail-open hazard ADR-021 names. `pkit schemas
validate` runs a **fragment-token-resolution lint** over every installed
capability's `grants.yaml` that catches exactly this: a grant token resolving to
no privilege in the merged catalog fails the gate. The lint reuses
`load_catalog`'s merge and `decide.py`'s token normaliser, so it agrees with the
runtime exactly (a token it passes is a token the hook binds).

### Deny/negation scopes are intentionally unsupported

Negation globs (`!*.ru`) in a domain-scoped grant are **explicitly rejected** with an error rather than silently accepted or partially enforced. Rationale (ADR-004, Alternatives considered, "Relabel `network-egress` as natively enforced…"): a tool-layer denylist is a false boundary — an agent's raw `bash curl` bypasses it at the sandbox layer, which is agent-blind. Advertising negation enforcement would overstate fidelity and violate COR-028's honesty discipline. Only positive allow-lists are supported; if you need to block a host, remove it from the allow-list rather than adding a negation glob.

## The rules of an agent run (ADR-066 point 5)

A command that starts agents with nobody watching may confine each run to rules of its own. The capability that ships the command declares them, and the privileges they name, in `.pkit/capabilities/<cap>/permissions/runs.yaml`, beside its grants fragment, keyed by the command whose runs they bind. Its shape is `.pkit/schemas/permission-runs.schema.json`. project-management's `fix-drift` is the first such command ([its README, "The rules of a fixer's run"](../capabilities/project-management/README.md#the-rules-of-a-fixers-run)).

**In the model, a run's rules are denies,** subject `all`, so COR-028 needs no change. One denies every call that none of what the run needs recognises. The others are a floor of denies. A deny prevails over every allow, the shared baseline's included, so a run may do only what the first deny leaves open, whatever else allows.

**No session's model composes the file.** `load_model` never reads it, and no hook sees it. The backbone's run command reads it at the commit the run is pinned to, fills in the run's folders, and projects it through this area's shared core, `projection.py`'s `project_run`. The adapter realises the result in that run's own settings, never in a settings file of the project's ([the adapters README, "The agent runner"](../adapters/README.md#the-agent-runner)).

**Its privileges take the catalog's entry shape, with three forms of their own,** which only a run fills in. They live in the run's file and never in the session catalog, so an older permission core never reads one, and the catalog schema's version does not move:

- `args`, the words a command starts with after its `cmd`, where `{working-copy}` and `{workspace}` stand for the run's folders, as in `git -C {working-copy} log`. A path-scoped privilege names those folders too.
- `kit: reading`, the backbone's reading commands, and `kit: queries`, each command another installed component declares a query, as `pkit <component or alias> <command>`. The backbone fills in both from the commit.
- `except`, the form ADR-066 point 5 adds: a call the rest of the recognizer matches, or every call where it has no other key, that none of the named privileges recognises.

**How the projection holds each deny.** The first deny becomes an allow list: each privilege it leaves open, in a native rule's form. Every other deny, the run's floor and the session model's denies for every agent or for the run's agent, is held in one of two ways. A deny that reaches nothing the allow list allows is held by the list, and each part of it a native rule can name is also written as a native deny. A deny that reaches something the allow list allows must be written as native denies there, which take it from the list; where no native rule can name it, the run is refused. Where the projection cannot tell that two recognizers never match the same call, it takes them to.

`pkit agents rules <capability>:<command>` shows the allow list, the denies and how each is held ([the CLI README, "agents rules"](../cli/README.md#agents-rules-capabilitycommand---agent-agent---json)). `pkit permissions overview` and `explain` list each run's rules under "RULES OF AGENT RUNS", with the capability that contributed them (ADR-016 point 7).
