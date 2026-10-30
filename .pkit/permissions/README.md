---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/permissions/*.py
        - .pkit/permissions/profiles/**
        - .pkit/schemas/privilege-catalog.yaml
        - .pkit/schemas/privilege-catalog.schema.json
        - .pkit/schemas/permission-grants.schema.json
        - .pkit/schemas/permission-profile.schema.json
        - .pkit/adapters/claude-code/permission-hook.py
        - .pkit/adapters/claude-code/permission-enforcement.yaml
        - .pkit/adapters/claude-code/settings/core/settings.json
        - src/project_kit/permissions.py
        - src/project_kit/workspace.py
        - src/project_kit/workspace_remove.py
        - src/project_kit/visibility.py
        - src/project_kit/run_rules.py
        - .pkit/schemas/permission-runs.schema.json
        - .pkit/permissions/project/grants.yaml
        - .pkit/permissions/project/config.yaml
        - .pkit/capabilities/project-management/permissions/grants.yaml
        - .pkit/rules/core.md
        - .pkit/skills/core/capability-author.md
        - .pkit/.gitignore
      record: [COR-007, COR-019, COR-028, PRJ-006, ADR-002, ADR-003, ADR-004, ADR-005, ADR-009, ADR-032, ADR-014, ADR-016, ADR-021, ADR-025, ADR-060, ADR-066]
      artefact:
        - .pkit/cli/README.md#surface
        - .pkit/cli/README.md#agents-rules-capabilitycommand---agent-agent---json
        - .pkit/cli/README.md#folders-a-sync-writes
        - .pkit/cli/README.md#init
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#workspace-remove-path---dry-run
        - .pkit/cli/README.md#agents-run-agent---folder-dir----commit-sha---rules-of-capabilitycommand---files-to-dir---limit-seconds---effort-level---json
        - .pkit/cli/README.md#schemas-validate-path
        - .pkit/cli/README.md#standard-flags
        - .pkit/adapters/claude-code/README.md#live-permission-enforcement-permission-hookpy
        - .pkit/adapters/claude-code/README.md#the-agent-workspace
        - .pkit/adapters/claude-code/README.md#the-probe-probe-confined-runpy
        - .pkit/adapters/README.md#the-agent-runner
        - .pkit/capabilities/project-management/README.md#permissions
        - .pkit/capabilities/project-management/README.md#the-rules-of-a-fixers-run
        - .pkit/capabilities/project-management/README.md#read-only-diagnostics--show-issue--show-pr
---

# The permission model

The permission model decides each tool call an agent makes, from grants of privileges to subjects: allow, deny or abstain ([COR-028](../decisions/core/COR-028-permission-model-realization.md)). Why it exists, and how people turn it on and do its common tasks, is in [the permission model's guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/permissions/README.md).

## Contents

<!-- pkit:contents -->
- [Grants and verdicts](#grants-and-verdicts)
- [Privileges and how they are recognized](#privileges-and-how-they-are-recognized)
- [Default-agent subject resolution](#default-agent-subject-resolution)
- [Compound commands (segment splitting + leading-`cd` strip)](#compound-commands-segment-splitting--leading-cd-strip)
- [A deny holds against the forms of its command](#a-deny-holds-against-the-forms-of-its-command)
- [Scope enforcement](#scope-enforcement)
- [The agent workspace](#the-agent-workspace)
- [Surgical denies for project-manager](#surgical-denies-for-project-manager)
- [Capability-contributed privilege *definitions*](#capability-contributed-privilege-definitions)
- [The rules of an agent run](#the-rules-of-an-agent-run)
- [The permission-prompt diagnostic loop](#the-permission-prompt-diagnostic-loop)
<!-- /pkit:contents -->

## Grants and verdicts

The model grants privileges to subjects, and the decision core gives each tool call one verdict from those grants (COR-028 point 1).

- **A subject** is `all`, `operator` or `agent:<name>`. `all` is every agent and the operator, and `operator` is the person who drives the session. "Default-agent subject resolution" below says which subject a call is decided for.
- **A grant** holds these keys, in the shape `.pkit/schemas/permission-grants.schema.json` gives:
  - `subject`
  - `privilege`: one or more privilege tokens, `[privilege-catalog:<id>]`
  - `effect`: `allow`, the default, or `deny`
  - `scope`: optional ("Scope enforcement" below)
- **A subject's grants** are its own and those of `all`.
- **Where the grants come from.** The decision core reads the model at each call. The model holds:
  - the guardrails, each denied to `all` ("Privileges and how they are recognized" below)
  - the active profile's grants ("Profiles" below)
  - the project's grants, in `.pkit/permissions/project/grants.yaml`, which `pkit permissions grant` and `revoke` write ([the CLI reference, "Surface"](../cli/README.md#surface))
  - the grants and privileges of each capability the manifest registers ("Where the deny lives" and "Capability-contributed privilege *definitions*" below)
- **The verdicts:**
  - **`allow`:** an allow grant of the subject covers the call within its scope, and no grant denies it. The harness runs the call with no prompt. For a Bash command, "Compound commands" below says when a grant covers it.
  - **`deny`:** a deny grant of the subject covers the call, or an allow grant covers it outside the grant's scope ("Scope enforcement" below). A deny wins over every allow, whatever the order of the grants. The harness refuses the call, and asks nobody.
  - **`abstain`:** no grant decides the call. The harness's own rules decide it: the allows and denies in its settings. The adapter writes them from its baseline and the model (COR-028 point 2). A call they neither allow nor deny goes to the harness's permission mode, which may ask the operator.
- **The posture** decides a call no grant covers. Under `lenient`, the default, the core abstains. Under `strict`, it denies. The posture is in `.pkit/permissions/project/config.yaml`.
- **A fault** while the hook decides gives an abstain, never a deny, so the hook fails open. The harness's native denies of the guardrails still refuse the forms of the guardrails' commands they name. That is the double lock ([the Claude Code adapter's README, "Live permission enforcement"](../adapters/claude-code/README.md#live-permission-enforcement-permission-hookpy)).
- **What the harness cannot enforce** is reported, never dropped (COR-028 point 3). The adapter declares what its harness enforces, and `pkit permissions diff` names the model's intent beyond it, such as network egress in Claude Code.
- **One loader, one core.** The hook and the `pkit permissions` commands build the model through the same loader. `pkit permissions probe` decides through the same core as the hook.
- **Only while the hook is registered.** With the hook off, only the harness's native rules hold. A grant only the hook realizes, such as of `text-filter`, `uv-run` or `workspace`, then allows nothing. An adapter's hook may also ask the operator where the core abstains, as Claude Code's does in two cases ([its README, "Live permission enforcement"](../adapters/claude-code/README.md#live-permission-enforcement-permission-hookpy)).

### Profiles

- **A profile** is a named set of grants and a posture. Three ship, in `.pkit/permissions/profiles/<name>.yaml`, each granting more than the one before: `read-only`, `non-destructive` and `autonomous`. `read-only` is strict, and the other two are lenient. A project's own profile, in `.pkit/permissions/project/profiles/<name>.yaml`, wins over a shipped one of the same name.
- **Activation:** `pkit permissions profile activate <name>` sets the posture, and layers the profile's grants under the project's own, which it never overwrites. It then writes the native rules it can, unless `--no-apply` is given. It registers no hook, which `pkit permissions enable` does ([the CLI reference, "Surface"](../cli/README.md#surface)).
- **Per machine:** the active profile is kept in `.pkit/permissions/project/active-profile.yaml`, which git ignores. Its posture goes into `.pkit/permissions/project/config.yaml`, which the project shares. So another clone takes the posture, and takes the profile's grants only once it activates the profile too.

## Privileges and how they are recognized

A privilege is a named thing a subject may be granted. The privilege catalog, `.pkit/schemas/privilege-catalog.yaml`, defines each under `privileges` (COR-028 point 1). A grant names one by its token, `[privilege-catalog:<id>]` (COR-019). `pkit permissions catalog` lists the catalog, each capability's privileges merged in.

The catalog's shape is `.pkit/schemas/privilege-catalog.schema.json`, and each privilege needs a `description` and a `recognize`. A project defines a privilege of its own only in a capability's catalog fragment ("Capability-contributed privilege *definitions*" below).

A privilege's `recognize` says which calls are its, in one or more of three forms:

- **`bash`:** a list of recognizers, each matched against one segment of a Bash command ("Compound commands" below). Each holds a `cmd` or a `pattern`. A `pattern` that matches recognizes the segment alone. Otherwise a recognizer with a `cmd` matches where each of the other keys it holds matches too:
  - `cmd`: the program, the segment's first word
  - `subcommand`: a list of words, one of which is the first word after the program that is no flag
  - `flag_any`: a list of flags, one of which the segment holds
  - `word_prefix_any`: a list of prefixes, one of which a word after the program opens with
  - `pattern`: a regular expression searched in the segment's words, joined by spaces, for a form the other keys cannot name
- **`tool`:** a list of the harness's tools, each recognized whatever its input, such as `WebFetch`.
- **`path`:** `tools`, a list of file tools, and `folders`, the folders inside which their target must lie ("The agent workspace" below). A folder is relative, and opens with no `/` or `~`, and holds no `..`.

The catalog's other keys:

- **`scope_type`:** `directory` or `domain`, what a grant's scope is matched against ("Scope enforcement" below).
- **`guardrail: true`:** the privilege is denied to `all`, and no grant allows around it. The shipped guardrails:
  - `destructive-fs`: recursive deletion with `rm`, in any flag form
  - `privilege-escalation`: `sudo`
  - `vcs-history-rewrite`: rewriting published history with `git push`, such as by `--force`

A grant matches a segment's words as the shell reads them. A deny matches more forms of them ("A deny holds against the forms of its command" below). A privilege a capability defines has a scoped key, `<cap>:<name>` ("Capability-contributed privilege *definitions*" below).

## Default-agent subject resolution

The hook resolves the subject for every PreToolUse call, in this order:

1. **`agent_type` present in the payload** → `agent:<agent_type>`. Claude Code sets this for spawned Task subagents.
2. **`agent_type` absent, and `.claude/settings.json` <!-- unanchored: named as the file the anchored hook reads, which sync generates under .claude/, a folder anchoring leaves out --> has `agent: X`** → `agent:X`. The main session runs as that agent, so all of the agent's grants apply, allow and deny. A missing, unreadable or malformed `settings.json` silently falls back to rule 3.
3. **`agent_type` absent, and no `agent` key in `settings.json`** → `operator`.

**Implication:** in a session with a configured default agent, the operator's `!`-typed command is also bound to that agent's grants.

**A session started with `--agent`:** the runs of project-management's `review-pr` name their agent on the command line, through the agent runner ([the adapters README, "The agent runner"](../adapters/README.md#the-agent-runner)). That sets the session's agent without changing `.claude/settings.json` <!-- unanchored: named as the file rule 2 reads, which sync generates under .claude/, a folder anchoring leaves out -->, the file rule 2 reads. So the hook may judge such a run as the project's default agent, or as `operator`, rather than as the agent it names. No grant for one agent counts in those runs until the adapter's probe shows which subject the hook judges ([the adapter's README, "The probe"](../adapters/claude-code/README.md#the-probe-probe-confined-runpy)).

**A confined run,** such as a fixer's, loads no project settings. So the hook is not registered there at all ("The rules of an agent run" below).

## Compound commands (segment splitting + leading-`cd` strip)

The decision core splits a compound Bash command into segments, and decides on what each segment matches. The command reaches the core as one string. The core splits it on `&&`, `||`, `|`, `;`, a background `&` and a newline, with a dumb regex splitter, which is no shell parser.

Within each segment the core reads the words as the shell does. It splits them at spaces and tabs, and removes quotes and backslashes by the standard library's POSIX quoting rules. So a grant or a deny matches `"--force"` as `--force`, and matches `git commit -m "fix: x"` as the command the shell runs.

Two prefix-strips apply before matching:

- **Env-prefix strip:** a leading `export` or `VAR=value` on a segment is dropped before matching, so `export GH_HOST=x && gh pr list` matches `gh pr list`. An assignment counts only where its name is written unquoted, as the shell reads it. A segment that only assigns, with an untrusted construct (below) in it, such as `X=$(./x.sh)`, is not dropped. The segment stays, and no grant covers it.
- **Leading-`cd` strip.** When the first segment is a bare `cd <path>` followed by `&&` or `;`, the core drops that segment. The core decides on the remainder against the unchanged grant model, so `cd src && gh pr list` auto-approves exactly as `gh pr list` would. The strip fails closed:
  - **Never a new grant.** The remainder is decided at the original working directory. So the strip never grants a directory-scoped privilege that the un-stripped command lacked.
  - **Only a bare `cd` is stripped:** a single path argument, parted from `cd` by a space or a tab, with:
    - no quotes
    - no `$()`
    - no backtick
    - no flags
    - no redirection but one that writes no file (below)

    A `cd "/x; rm -rf ~" && …` is not a bare `cd`, so it is not stripped and falls through to the full-command path, where its deny still binds. Deny-wins is never weakened.
  - **No `cd` is stripped from a command holding any of these,** its `cd` included, each described below:
    - an untrusted construct
    - a word the core cannot read as the shell does
    - a leading assignment of the kinds that keep every grant from allowing

    Such a command is decided whole, as `cd {a,b} && git status` is.
  - **The remainder is decided like any command.** An untrusted construct keeps every grant from allowing the remainder, as such a construct does anywhere in a command (below). So `cd /x && echo z > ~/f` and `cd /x && gh $(rm -rf ~)` prompt rather than slip through. So does a redirect into the agent workspace, as in `cd /x && cat > .agent-workspace/body.md <<'EOF'`, since the workspace grant covers the file tools only.
  - **A pipe is decided segment by segment.** The `cd` strip does not touch pipes, and `|` is not a `cd` separator. So `cd /x && gh … | sh` decides exactly as the bare `gh … | sh` does, and both abstain, since every segment needs its own allow (below).

The widenings taken are the leading-`cd` strip and the removal of a redirection that writes no file (below).

**Every segment needs its own allow.** The core allows a compound only when an allow grant covers each segment the splitter yields. A segment that matches no privilege, or only privileges no allow grant of the subject reaches, makes the core abstain. The call then goes to the harness's native rules, and a strict posture denies it instead.

So where only `gh` is granted, `gh pr list | sh` and `gh pr list & python3 x.py` abstain, as does `python3 x.py` on the line after `gh pr list`. So does a pipe into a filter no grant covers, such as `gh pr list | jq .`. A compound whose every segment is granted, such as `git diff | git apply --check`, is allowed.

### The read-only text filters and `uv run`

Two catalog privileges cover the programs a compound most often pipes into or runs. A compound of these programs and other granted ones is then allowed, each segment still needing a grant of its own:

- **`text-filter`** recognizes programs whose only effect is their standard output. They write no file, reach no network, run no other program and change no shell state. Every shipped profile grants it to `all`, and it carries no path scope.
  - **The programs:** `cat`, `head`, `tail`, `wc`, `cut`, `tr`, `grep`, `egrep`, `fgrep`, `ls`, `cmp`, `comm` and `paste`. The list goes on with `basename`, `dirname`, `realpath`, `pwd`, `true`, `false`, `seq`, `sleep`, `stat`, `du` and `which`.
  - **`sort`, `uniq` and `diff`,** each in a form that writes no file and runs no other program. The form holds no pathname pattern that could expand to such a form. The catalog's comments list the forms.
- **`uv-run`** recognizes `uv run`, which runs any program it is given in the project's environment and confines nothing. A grant allows whatever that program does. A deny reads the command as the wrapper `uv`, never as the program behind it, so no guardrail reaches `uv run rm -rf ~`. No shipped profile grants it, so a project that wants it grants it in its own `grants.yaml`.

Each recognizer of the two is a `pattern` or names a subcommand. So a grant of either writes no native allow rule, and only the hook realizes the grant.

Neither recognizes a program that writes a file or runs another, such as `sed`, `awk`, `find`, `xargs`, `tee` or `rg`. Nor does either recognize `echo`, `printf` or `jq`. So under a shipped profile, `grep x f | head` is allowed for every agent, and `grep x f | sed s/a/b/` abstains.

What a granted program reads from a pipe is within its own grant, as its arguments are. A `pkit` confirmation that guards a person's decision reads no answer from a pipe ([the CLI README, "Standard flags"](../cli/README.md#standard-flags)).

Recognition goes by the program's name, as for every privilege. A shell alias or function under one of these names runs what it names, unasked. Each of the two privileges is sound only where its names reach the system's own programs.

### What keeps a grant from allowing

Three things in a Bash command keep every grant from allowing it, each described below:

- an untrusted construct
- a word the core cannot read as the shell does
- a leading assignment that changes which program runs, or one written with a quote or a backslash

**An untrusted construct keeps every grant from allowing.** A Bash command that holds one, with or without a leading `cd`, makes the core abstain, and a strict posture denies it instead. The constructs are these, and the scan finds each inside quotes as well:

- a backtick
- a `<` / `>` redirection other than one that writes no file (below)
- a `(`, which opens every substitution:
  - `$(…)`
  - `<(…)` / `>(…)`
  - zsh's `=(…)`
  - zsh's glob qualifiers and parameter flags that run code
- a `$`, which opens every expansion, such as `${X@P}` and `$[…]`

**So does a word the core cannot read as the shell does:**

- a quote or a backslash that does not close, as where the splitter cuts a quoted `;`
- whitespace other than a space, a tab or a newline, such as a no-break space
- a word opening with `#`, a comment the shell drops
- a brace expansion, such as `{a,b}` or `{1..3}`, which the shell turns into several words
- a program name holding whitespace, such as `'make test/x'`

**And so does a leading assignment that changes which program runs, or one written with a quote or a backslash.** Each such assignment is stripped for the denies, so `PATH=/tmp/x sudo id` is denied.

- **The variables that change which program runs.** The list names a family of variables, and is no boundary:
  - a search path, `PATH` or any other name ending in `PATH`, and the dynamic loader's `LD_*` and `DYLD_*`
  - the variables that name the startup files a shell reads first, such as `BASH_ENV`, `ENV` and `ZDOTDIR`
  - the options of Python, Perl, Ruby, Node and Java, which load code ahead of the program's own
  - zsh's `NULLCMD` and `READNULLCMD`, which name the program a command of redirections alone runs
- **A program's own setting,** such as `GIT_PAGER=cat`, is stripped and allowed: what a granted program is told to run is the grant's breadth. A setting that changes which configuration the program reads may still keep a deny from telling (below).
- **An assignment written with a quote or a backslash** is never allowed by a grant. Only a quoted argument is matched as the shell passes it on.

A segment led by `export` runs no program. `export` takes each word after it as a name or an assignment, so `export git PATH=/tmp/x` sets `PATH` and runs no `git`. The segment's assignments are judged as above, and no grant on a program covers the segment. A segment led by `builtin export` or `command export` stays a program no grant covers.

Each word after `export` must be a plain name or assignment. Any other word, such as `PAT?=bin`, keeps every grant from allowing.

So where `gh` and `git` are granted, `gh pr list > ~/.bashrc`, `gh pr list $(python3 x.py)` and `PATH=/tmp/x gh pr list` abstain, and the harness's native rules decide each. A quoted argument alone is none of these: `git commit -m "fix: x"` is allowed, and `git push origin main "--force"` is denied as `--force` is.

For a grant, outside an `export`, a glob is read as written.

### A redirection that writes no file

A redirection that writes no file is no untrusted construct. The core removes such a redirection before it splits the command, and decides the command as it would without the redirection:

- an fd duplicated onto stdout or stderr, or closed, such as `2>&1`, `1>&2`, `>&2` or `2>&-`
- output discarded to `/dev/null`: `>`, `>>`, `2>`, `2>>`, `&>` or `&>>`, with or without a space before `/dev/null`

So where `git` and `gh` are granted, `git status 2>&1 | gh pr list` and `cd /x && git log >/dev/null` are allowed. A deny binds on a program behind such a redirection, so `2>/dev/null rm -rf ~` is denied. The removal ignores quotes, as the scan for untrusted constructs does.

Each form counts only where these hold:

- **A whole word.** Each form counts only as a whole word, with an fd number of one digit or none, and the target exactly `/dev/null`, unquoted.
- **A duplicated fd.** After `>&` or `<&` comes `1`, `2` or `-` alone.
- **Last in its segment.** `&>` and `&>>` count only last in their segment.

A segment left with redirections and assignments alone, or behind only a word such as `{` or `do`, keeps the command untrusted.

A lookalike stays untrusted, such as `2>&1t`, `{fd}>/dev/null` or `>&word`. So does every other redirection, such as `> out.txt`, `< in.txt`, `>|`, `<>`, a here-string or a heredoc.

### Denies, and what an abstain says

A deny on any segment still wins over every allow, and over an untrusted construct.

The abstain's reason names each uncovered segment's program where that is a bare word, and never its arguments. The reason for an untrusted construct lists the kinds of construct, and none of the command's text.

## A deny holds against the forms of its command

A deny, a guardrail's included, matches its command in more forms than a grant does. A grant matches a command as it is written, and a deny also matches these forms of it, as programs read them:

- a short flag inside a bundle, such as `-f` in `git push -uf`
- a long flag cut to a prefix, such as `--force-w`, which git reads as `--force-with-lease`
- a long flag with its value after `=`, such as `--force-with-lease=main`, or behind one dash, such as `-force`
- a program named in one of these ways:
  - by its path, such as `/usr/bin/sudo`
  - by zsh's `=sudo`
  - in another case, such as `Git`, which macOS runs as `git`
- a subcommand behind the options before it, such as `push` in `git -C . push --force`

The core reads these forms from a structured recognizer's `cmd`, `subcommand` and `flag_any`. Each reading errs toward the deny, so a prefix several long flags share reads as each. So does an option that is itself a prefix of a denied one, such as `--proxy` of `--proxy-insecure`.

A recognizer's regex `pattern` is matched with a program's path cut to its name, and with the options before a subcommand left out. The core reads up to 64 places where the subcommand may stand behind an option's value, and past them it abstains. Otherwise the regex is matched as written, so it spells each form of the flags it names. An example is the shipped `destructive-fs` regex, which spells `--recursive` cut down to `--r`.

The `vcs-history-rewrite` guardrail also names `--mirror`, which force-updates every ref the remote holds. It names a refspec opening with `+`, as in `git push origin +main`, through the recognizer field `word_prefix_any`.

**Where a deny may bind on what the core cannot see, no grant allows the command.** The core then abstains, naming the deny, and a strict posture denies. Two things keep the core from seeing:

- **A pathname pattern,** such as `--forc[e]` or `*`, which the shell expands to the names of files. A glob character counts outside quotes alone, so `git push origin '[+]main'` is read as written.
  - **For a structured recognizer,** the core cannot tell where such a pattern stands for the program or subcommand, or may open with `-` or `+`.
  - **For a regex `pattern`,** the core cannot tell where such a pathname pattern stands anywhere in a segment of the program the regex opens with. Where the regex plainly opens with no program, that holds for a segment of any program.
- **An assignment that changes the program's configuration.** Such an assignment keeps a deny from telling on any segment of the program the deny names, so `HOME=/tmp/x git status` abstains.
  - **The variables:**
    - `HOME`
    - the XDG base directories
    - any name holding `CONFIG`, such as `GIT_CONFIG_GLOBAL`
    - git's repository directories
  - **Where such an assignment counts:** in front of a command, for that command, and in a segment that only assigns or exports, `builtin export` included, for the segments after it.

**Where Claude Code may allow what the core abstains on for a guardrail, the operator is asked, outside auto and bypass mode.** A harness's native rules may allow a command the core abstains on, as Claude Code's baseline allows `git push origin --forc[e]` by `Bash(git:*)`. So the core names each guardrail among the subject's denies that may bind on such a command in a form the core cannot see. An adapter may use those names to ask the operator rather than abstain.

[The Claude Code hook](../adapters/claude-code/README.md#live-permission-enforcement-permission-hookpy) asks the operator on such a command, except in auto and bypass mode. A project's own deny, such as the project manager's on raw `gh` mutations, is no guardrail, so the core names none for it. Where the core cannot tell such a deny, it abstains. The deny side stays a speed bump all the same, not a security boundary.

What the forms leave out stays unseen, and nothing asks about it. A git alias or refspec set in a configuration git already reads, or through `git -c` or a granted `git config`, is the grant's breadth. A program behind a wrapper, such as `env` or `command`, is read as the wrapper. No shipped grant covers one, so the core abstains, but a project's grant on a program runner, such as `xargs`, would allow what it runs.

An abstain for a construct the core cannot read, such as `git push origin $F`, names no guardrail either, so the harness's native rules decide the command. So does a wrapper the harness allows, as Claude Code's baseline allows `find`, and with it `find . -exec rm -rf {} +`, which no native deny's prefix matches.

## Scope enforcement

Grant scope globs constrain the reach of an allow grant. The dimension they are matched against depends on the privilege's `scope_type` in `.pkit/schemas/privilege-catalog.yaml`:

- **`directory` scope,** such as `docker`'s, and the default where a privilege declares no `scope_type`: grant scope globs are matched against the request's `cwd` with `fnmatch`. A request outside the listed paths is denied. The hook enforces this at decision time. This is no OS-level confinement boundary.
- **`domain` scope,** such as `web-fetch`'s: grant scope globs are matched against the hostname of the request's URL with `fnmatch`, with positive allowlist semantics. The grant permits only URLs whose host matches at least one glob. A request whose host matches none, or that carries no URL that parses, is denied.
- **No scope:** the grant is unconstrained, for any working directory and any host.

An example of a `domain` scope, in `.pkit/permissions/project/grants.yaml`:

```yaml
- subject: agent:researcher
  privilege: "[privilege-catalog:web-fetch]"
  scope: ["docs.python.org", "*.github.com"]
  effect: allow
```

This grant allows `researcher` to fetch from `docs.python.org` or any subdomain of `github.com`, and denies every other host.

A scope confines a privilege: a scoped allow denies the privilege outside its scope. The agent workspace's folder is no grant scope, but part of its privilege's recognizer, `recognize.path` ("The agent workspace" below).

### Deny/negation scopes are intentionally unsupported

A negation glob, such as `!*.ru`, in a grant's scope is rejected: each call the grant covers is denied, with a reason that says why. It is neither silently accepted nor partly enforced.

Only positive allowlists are supported, so to deny a host, remove it from the allowlist rather than add a negation glob.

## The agent workspace

Every checkout of a project has one agent workspace: `.agent-workspace/` at its root. Agents keep their intermediate files there, and nowhere else outside the repository, as the workspace rule in `.pkit/rules/core.md` says. The workspace's design is a path-scoped allow, recognized from a file tool's target path, with no exception for the shell. Every harness adapter meets this contract:

- **What it holds:** agents' intermediate files, such as pull-request and issue bodies, scripts, captured output and notes.
- **Per checkout, never committed:** `pkit init` and `pkit sync` create the folder, and exclude it through the repository's local exclude file in the common git directory:
  - each worktree has its own folder at its own root
  - one exclude entry covers all of them
  - nothing in them reaches a commit

  That entry covers the clone it was written in, and nothing in the folder is shared between clones. `init` recommends the same line for the project's committed `.gitignore`, which covers every clone and which pkit never writes ([the CLI README, `init`, step 4](../cli/README.md#init)).
- **Granted to every agent, for the file tools, and only there.** The catalog's `workspace` privilege is a path-scoped allow (`recognize.path`), recognized only where both of these hold, and never for the tool alone:
  - the tool is a file tool the privilege lists: `Read`, `Write`, `Edit`, `MultiEdit` or `NotebookEdit`
  - its target lies inside `.agent-workspace/` of the project root, or of another working tree of the same repository
- **Every shipped profile grants the privilege** to `all`, `read-only` included.
- **Prompts, not confinement:** the privilege reduces prompts on the allow side, keyed on the target path, and confines nothing. A grant of the privilege can neither reach nor deny a file anywhere else. Outside the folder the privilege does not apply, and a request is decided exactly as without it.
- **What lies inside:** a target whose path resolves inside the folder, symlinks resolved. A link out of the folder is outside.
  - **The folder counts only as the checkout itself holds it.** A symlinked `.agent-workspace` is never the workspace, and a catalog folder entry that is absolute or climbs out with `..` is never recognized. Another working tree counts only when git registered it for the same repository, and another repository's workspace never does.
  - **A repository or worktree nested inside the folder is not the folder.** When any directory from the folder down to the target holds a `.git` entry, the target is another checkout's.
  - **An existing file with more than one link is not inside either.**
- **No shell command is the workspace's.** A redirect, a here-document or an `rm` into the folder is judged like any other shell write, the leading-`cd` strip included ("Compound commands" above). A remainder with a redirect into the folder still abstains. Write intermediate files with the file tools.
- **Files leave through `pkit workspace remove`, never through `rm`.** The command tests each path after the shell expanded it, and removes nothing unless every path lies inside the folder ([the CLI README, `workspace remove`](../cli/README.md#workspace-remove-path---dry-run)). The permission model decides it as it decides any `pkit` command, so the workspace privilege does not cover it. Agents remove only what they wrote.
- **A capability's lasting state lies under its own name.** The folder is shared by every agent working in the checkout. A capability keeps state that must last under a direct child named after itself, as project-management keeps its drift queue. The removal command refuses any path at or under such a child.
- **Realized by the hook, never as a session-wide rule.** The projection reports a `workspace` grant as `runtime`, never as a native allow. An adapter whose harness does not already approve the folder emits the narrowest path-scoped rule its harness offers, and one whose harness does emits nothing.
- **In Claude Code:** [the Claude Code adapter's README, "The agent workspace"](../adapters/claude-code/README.md#the-agent-workspace), says which of the two Claude Code does. It also says that the adapter's enforcement declaration names the dimension `path-scoped-allow`.
- **A prompt there is a defect** ("A prompt for the agent workspace is a defect" below).

<a id="surgical-deny-blocking-raw-gh-mutations-for-project-manager"></a>

## Surgical denies for project-manager

Two privileges of the backbone catalog let a deny aim at the raw `gh` commands that the project-management capability's own scripts replace:

- **`issue-tracker-write`** recognizes the raw `gh` mutations that bypass the capability's validating scripts. They are `gh issue create`, `edit`, `comment`, `close` and `reopen`, and `gh pr create`, `edit`, `merge`, `close` and `reopen`. It matches only those mutations: no read, such as `gh issue view` or `gh pr view`, and not `gh api`.
- **`issue-tracker-read-raw`** recognizes the three raw read views that the capability's clean-output verbs replace: `gh issue view`, `gh pr view` and `gh pr diff`. It never matches `gh pr checks`, `gh run`, `gh api`, `gh issue list` or `gh pr list`, and never a mutation, which `issue-tracker-write` covers or leaves open.

The capability denies both to its `project-manager` agent, and routes the agent to `pkit project-management show-issue` and `show-pr` for reads ([its README, "Permissions"](../capabilities/project-management/README.md#permissions)). The harness rejects a denied call without prompting the operator, so the agent adapts to the clean verb.

<a id="where-the-deny-lives-adr-016"></a>

### Where the deny lives

The deny is a grant that the project-management capability contributes, in `.pkit/capabilities/project-management/permissions/grants.yaml`. It is no manual grant in `.pkit/permissions/project/grants.yaml`, which stays empty for this policy. The model takes such grants from each capability that the manifest's `components:` list registers. A capability folder the manifest does not register contributes nothing (install-state-as-gate).

`pkit permissions overview` lists the deny under "CAPABILITY-CONTRIBUTED DENIES".

When `project-manager` calls `gh issue edit`, the request matches two privileges:

- **`issue-tracker`,** the broad `cmd: gh` recognizer, is allowed once the active profile grants it to the agent.
- **`issue-tracker-write`,** the mutation pattern, is denied by the capability's grant.

A deny wins over every allow, whatever the order of the grants. So the capability's deny holds even where the `autonomous` profile grants `issue-tracker` to `all`.

The capability scripts' own `gh` calls are unaffected. They run inside the `pkit` subprocess, below the hook: they are no Claude Code tool calls, so the hook does not enforce on them.

<a id="capability-contributed-privilege-definitions-adr-021"></a>

## Capability-contributed privilege *definitions*

A capability may define privileges of its own, beside the denies it ships ("Where the deny lives" above). An installed capability may ship a **privilege-catalog fragment** at `.pkit/capabilities/<cap>/permissions/privilege-catalog.yaml`, which the core merges into the central catalog. So a capability ships a privilege's definition and its deny together, with no edit to the backbone catalog, which `pkit sync` overwrites.

- **One shape.** The fragment reuses the document shape of `.pkit/schemas/privilege-catalog.yaml`, with no new schema.
- **Installed capabilities only.** As for grants, only a capability the manifest registers contributes, and an orphan folder contributes nothing.
- **The merge rule:** additive only, rejecting collisions, and forbidding guardrails. Each fragment id is rewritten to a capability-scoped key, `<cap>:<name>`. So a fragment can extend the recognized vocabulary in its own namespace, but can never overwrite a backbone or peer privilege. A `guardrail: true` fragment entry is rejected.
- **Referencing one.** A grant references a scoped privilege with the COR-019 token whose id half carries the scope, `[privilege-catalog:<cap>:<name>]`, per COR-019's id-scope clarification.
- **Inert until granted.** A fragment privilege is inert until a grant references it. What narrows an agent's reach is the deny grant the capability also ships. A tool-call deny is a speed bump that shapes behaviour, not a security boundary.
- **Visible.** `pkit permissions overview` attributes each merged privilege to its contributing capability, and shows any rejected fragment.

### Authoring a fragment (`pkit permissions scaffold <cap>`)

Run `pkit permissions scaffold <cap>` to stamp the skeleton of both hand-authored fragment files, with the correct shapes and inline guidance on their footguns. The command stamps `privilege-catalog.yaml` and `grants.yaml` into the capability's `permissions/` folder. It refuses an unknown capability, and refuses to clobber an existing fragment. It also refuses a capability whose files the project receives as synced copies ([the CLI reference, "Folders a sync writes"](../cli/README.md#folders-a-sync-writes)).

The scaffold's guidance captures two footguns:

- **A fragment privilege key is authored bare.** The loader applies the `<cap>:` scope.
- **A grant references it with the scoped token,** `[privilege-catalog:<cap>:<name>]`. A bare grant token against a fragment privilege resolves to no merged privilege, so the deny silently does not bind: a fail-open hazard.

`pkit schemas validate`, run with no path, fails a grant token that resolves to no privilege in the merged catalog, in every installed capability's `grants.yaml`. It merges the catalog and reads tokens as the hook does. So a token it passes is a token the hook binds ([the CLI README, "schemas validate"](../cli/README.md#schemas-validate-path)).

**Note:** the command is paired with the `capability-author` skill, step 6b.

<a id="the-rules-of-an-agent-run-adr-066-point-5"></a>

## The rules of an agent run

A command that starts agents with nobody watching may confine each run to rules of its own. The capability that ships the command declares them, and the privileges they name, in `.pkit/capabilities/<cap>/permissions/runs.yaml`, beside its grants fragment. The file keys them by the command whose runs they bind, and its shape is `.pkit/schemas/permission-runs.schema.json`. project-management's `fix-drift` is the first such command ([its README, "The rules of a fixer's run"](../capabilities/project-management/README.md#the-rules-of-a-fixers-run)).

**In the model, a run's rules are denies,** for every subject, `all`. One rule denies every call that none of the privileges the run needs recognizes. The run's other rules are a floor of denies. A deny prevails over every allow, the shared baseline's included, so a run may do only what the first deny leaves open, whatever else allows.

**No session's model composes the file,** and no hook sees it. The backbone's run command, `pkit agents run`, reads the file at the commit the run is pinned to, and fills in the run's folders. It then projects the file through the shared decision core. The adapter realizes the result in that run's own settings, never in a settings file of the project's ([the adapters README, "The agent runner"](../adapters/README.md#the-agent-runner)).

**The run's privileges take the catalog's entry shape, with three forms of their own,** which only a run fills in. They live in the run's file and never in the session catalog:

- `args`: the words a command starts with after its `cmd`, where `{working-copy}` and `{workspace}` stand for the run's folders, as in `git -C {working-copy} log`. A path-scoped privilege names those folders too.
- `kit`: `reading`, the backbone's reading commands, or `queries`, each command another installed component declares a query, as `pkit <component or alias> <command>`. The backbone fills in both from the commit.
- `except`: a call the rest of the recognizer matches, or every call where it has no other key, that none of the named privileges recognizes.

**How the projection holds each deny.** The first deny becomes an allowlist: each privilege it leaves open, in a native rule's form. The other denies are the run's floor, and the session model's denies for every agent or for the run's agent. Each is held in one of two ways:

- **Held by the list:** a deny that reaches nothing the allowlist allows. Each part of it a native rule can name is also written as a native deny.
- **Written as native denies:** a deny that reaches something the allowlist allows. The native denies take it from the list, and where no native rule can name it, the run is refused.

Where the projection cannot tell that two recognizers never match the same call, it takes them to match the same call.

`pkit agents rules <capability>:<command>` shows the allowlist, the denies and how each is held ([the CLI README, "agents rules"](../cli/README.md#agents-rules-capabilitycommand---agent-agent---json)). `pkit permissions overview` and `explain` list each run's rules under "RULES OF AGENT RUNS", with the capability that contributed them.

<a id="the-permission-prompt-diagnostic-loop-prj-006"></a>

## The permission-prompt diagnostic loop

The diagnostic loop is opt-in and recommend-only. It records each call the hook abstained on, and reports what would remove each prompt. It has two halves, one in the hook and one in the CLI.

- **Capture, in the hook.** While the loop is off, the default, the hook does one read of a marker and logs nothing. While it is armed, the hook appends each call it abstained on to a local log, after the decision is made. A fault in capture changes no decision and never breaks the hook's fail-open.
- **What the log holds.** The hook observes only its own abstain, not whether the harness then prompted. So the log holds a superset of real prompts. The report states its coverage, never a predicted fall in the number of prompts.
- **Arm, disarm and report, in the CLI:** `pkit permissions diagnose on`, `off`, `status` and `report`.
  - **The marker,** `.pkit/permissions/project/diagnose.yaml`, carries a time to live, so a session expires by itself.
  - **The log,** `.pkit/permissions/project/diagnose-log.jsonl`, is capped in size and drops its oldest entries first. It redacts each command's tail by default.
  - **Both files are ignored by git,** through the `.pkit/.gitignore` that pkit owns and renders.
- **The report's groups.** The report groups the raw command text, to order and explain its recommendations. The groups are advisory for ranking only, and never authorize a change.
- **Nothing applied.** The loop applies no fix. Writing a new catalog privilege is never a fix, and stays the operator's task.

<a id="two-sharpening-axes-on-the-report-issue-317"></a>

### Two sharpening axes on the report

The report adds two static axes. They turn raw counts of abstains into counts of real prompts, split by cause. Both are computed over the logged command text, which is redacted, and both stay recommend-only.

- **Prompted vs auto-allowed.** Each logged record is an abstain of the hook's, to which the harness then applies its own allow patterns. Those are the `permissions.allow` patterns of the live `settings.json` and `settings.local.json`. The report matches each record against them, flat, and counts a record that matches none as a real prompt:
  - **A Bash command** matches where its leading words are exactly a `Bash(<prefix>:*)` pattern. A command of shell shape, such as one holding `&&`, `|`, `;` or `$(…)`, never matches one pattern, so it always counts as a real prompt.
  - **Another tool's call,** such as `Read` or `Edit`, matches where its tool is allowlisted.
  - **The headline** gives the real prompts apart from the auto-allowed rest: `outcome: N real prompt(s) of M captured (M−N auto-allowed by the live settings.json flat matcher — NOT prompts).`
- **Allowlisted-but-compound vs genuinely-missing.** Of the real prompts, the report splits each command on its shell operators. It tests every segment against the same matcher, except a bare `cd <path>`.
  - **Allowlisted-but-compound:** a command of shell shape whose every segment matches alone. It is an allowlisted command defeated only by compounding. The report recommends eliminating it at its source, by a decomposition or a butter verb. A butter verb is one clean command for the job, as `pkit project-management show-issue` replaces a piped `gh issue view`.
  - **Genuinely-missing:** a real allowlist gap: an uncovered segment head, a bare uncovered command, or an un-allowed tool.
  - **The headline** carries the split, and the line of the shell-shape group is tagged with it.
- **Scope and honesty.** Both axes are static over redacted text, so a `Bash(<prefix>:*)` longer than the head the redaction keeps cannot match as a prefix. They leave `deny` patterns out of scope: a logged record is one the hook abstained on, never one it denied. The numbers promise no fall in live prompts.

### A prompt for the agent workspace is a defect

Every agent is granted the agent workspace, so a file tool's prompt there is a defect, never an allowlist gap to tune around. Its cause is a missing active profile, or enforcement that is off: worth a report, not a new allow rule.

- **The tag.** Capture tags each abstain `workspace: true` or `false`. The tag says whether the decision core's own recognizer places a file tool's target in the workspace ("The agent workspace" above). The path itself is never logged.
- **The band.** The report puts each abstain tagged `true` in a `workspace` group, under a **DEFECTS** band of its own, ahead of every recommendation.
- **A shell command** that writes into the folder is not tagged. It is judged like any other shell write, so its prompt is an ordinary one.
