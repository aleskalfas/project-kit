"""Permission decision core (per COR-028 / ADR-003).

Harness-neutral, propagated, standalone module — imported by BOTH the
claude-code PreToolUse hook (which runs in the adopter tree at decision
time, where the global `pkit` is not importable) AND the `pkit permissions`
CLI. ADR-002's same-code invariant requires they decide identically, so the
logic lives here once and both call it.

Dependency direction (ADR-003): CLI and hook import this; this imports neither
`src/project_kit` nor any adapter. Recognizers arrive as catalog *data*
(privilege-catalog.yaml), never as adapter code.

Pure logic operates on plain dicts (a loaded grant model + privilege catalog);
the loaders are thin helpers. No third-party deps beyond PyYAML for the loaders
(the pure `decide()` path needs none).
"""

from __future__ import annotations

import fnmatch
import os
import re
import shlex
import stat
from typing import Any

# The formatter leaves the `decide()` verdict path alone: these regexes, and
# the two runs of functions below that are fenced the same way. ADR-032 and
# ADR-060 hold that path byte-identical to its prior form, and
# tests/test_permissions_cli.py pins it against the default branch, so a
# formatting pass may no more rewrite it than a hand edit may.
# fmt: off

# A grant's privilege value is the COR-019 token `[privilege-catalog:<id>]`
# (or a list of them); strip to the bare id for matching against the catalog.
# The id half admits an OPTIONAL capability scope (`<cap>:<name>`) so a
# capability-contributed privilege (ADR-021) is referenced as
# `[privilege-catalog:trip-planning:ad-hoc-scraping]`. This is the COR-019
# token-grammar *clarification*: the namespace stays `privilege-catalog`; the
# id half gains permitted internal structure. The capture group keeps the WHOLE
# id half (including any embedded `:`), so the token round-trips to the catalog
# key exactly — a mis-resolved scoped token would empty the grant's privilege
# match and the deny would silently not bind (a fail-open hazard).
_TOKEN = re.compile(r"^\[privilege-catalog:([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\]$")
# The segment separators: `&&`, `||`, `|`, `;`, a background `&` and a newline
# (#1917). The shell runs the command after a newline or a lone `&` as it runs
# the one after `;`, so each starts a segment that needs a grant of its own.
# `&&` and `||` come before `&` and `|` so a double one is never read as two.
_SEP = re.compile(r"\s*(?:&&|\|\||\||;|&|\n)\s*")
# An assignment word, `NAME=value` or `NAME+=value`, as the shell reads one in
# front of a command (#1942): the `+=` form appends, and is stripped like the
# other, so a deny on the command behind it binds.
_ENVVAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")

# The leading-`cd` strip (ADR-025 Phase 1). A bare `cd <path>` prefix changes
# only the cwd — which the intent layer never confines — so stripping it reveals
# the already-granted intent of the remainder; it grants nothing new. We strip
# ONLY a bare `cd <single-path-arg>`: no quotes, no `$()`, no backtick, no
# redirection, no flags. Anything more complex is NOT stripped (falls through to
# existing behaviour). `_CD_SEP` matches the FIRST `&&` / `;` separator (the only
# separators that sequence a directory change before a granted command — a bare
# `cd src | gh …` makes no shell sense, so `|` / `||` are deliberately excluded).
_CD_SEP = re.compile(r"\s*(?:&&|;)\s*")
# Constructs the dumb splitter cannot be trusted on (ADR-004 dp-4 / ADR-025
# decision 2): a `$`, a backtick, a `<` / `>` redirection, and a `(`. The `(`
# opens every substitution the shells offer: `$(…)`, `<(…)` / `>(…)`, zsh's
# `=(…)`, and zsh's glob qualifiers and parameter flags, such as `*(e:…:)` and
# `${(e)…}`, which run code. The `$` opens every expansion (#1942): a
# variable's value, which the core never sees and which some forms evaluate as
# code, such as bash's `${X@P}`, `$[…]` and an arithmetic offset `${X:$Y}`, or
# zsh's `$~X`, and the quotes `$'…'` and `$"…"`, which the shell reads
# otherwise than the core does. A command holding any of them ANYWHERE, even
# inside quotes, with or without a leading `cd`, is never allowed by a grant
# (#1917): `decide()` abstains, or denies under a strict posture, because a
# per-segment matcher is structurally blind to what these compose into. A deny
# still wins. It stays a plain scan of the command string, not a parse
# (ADR-025 point 3). A quote is not in the set: the core removes quotes as the
# shell does before it matches (`_words()`), so a quoted word is the word the
# shell runs.
#
# `|`, like `&&`, `||` and `;`, is not in this set because the splitter
# separates on it: each side of a pipe is a segment of its own, and `decide()`
# allows a compound only when an allow grant covers EVERY segment (ADR-025
# point 2: an unrecognized command in any segment abstains, never auto-allows).
# So `gh … | sh` abstains, since nothing grants `sh`, with or without a leading
# `cd`, and `gh … | jq` abstains too unless a grant covers `jq`. A pipe whose
# every side is granted, such as `git diff | git apply`, still allows: that is
# no new widening, since each segment carries its own grant (ADR-025 point 6).
#
# A redirection that writes no file is removed before this scan, and before
# the command is split (`_HARMLESS_REDIRECTION`, #2002), so its `<` or `>`
# is not counted here. Every other `<` or `>` still is.
_UNTRUSTED = re.compile(r"""[$`<>(]""")
# A redirection that writes no file and changes no program (#2002, ADR-025
# point 2): an fd duplicated onto stdout or stderr or closed, `N>&M`, `N<&M`
# or `N>&-`, and output discarded to `/dev/null`, `N>` or `N>>`, or `&>` or
# `&>>`, with or without a space before `/dev/null`.
# - N is one digit, or is left out, as in `>&2`. zsh reads a longer number
#   before `>` as an argument of its own, and dash reads no longer fd.
# - After `>&` or `<&` comes 1, 2 or `-` alone, so output goes only where the
#   command's own stdout or stderr already goes. `>&word` with any other word
#   writes to the file `word`, and another fd may be one the shell holds open
#   on a file, such as after an earlier `exec 3>file` in a shell that lives
#   on. The target is exactly `/dev/null`, unquoted.
# - Each counts only as a whole word. Before it stands the start of the
#   command, or a space, a tab or a newline with no backslash before it.
#   After it stands the end, a space, a tab, a newline, `|`, `;` or `&`. So
#   `gi2>&1t`, which zsh runs as `gi2` writing to a file named `1t`, is no
#   such word. Nor is `{fd}>/dev/null`, which stores the new fd's number in
#   the variable `fd`, nor `a\ 2>&1`, whose `2` the shell passes on in `a 2`.
# - `&>` and `&>>` count only last in their segment. A shell without them,
#   such as dash, reads the `&` as running the command in the background, and
#   would run the words after `/dev/null` as a command of their own. bash 3.2
#   rejects `&>>` outright.
# - The scan ignores quoting. Inside quotes such a word is part of an
#   argument, and removing it changes only that argument's text: the quotes
#   stay, and whitespace stays on both sides, so no word joins another.
_HARMLESS_REDIRECTION = re.compile(
    r"(?:\A|(?<=[ \t\n]))(?<!\\[ \t\n])"
    r"(?:[0-9]?[<>]&[12-](?=[ \t\n|;&]|\Z)"
    r"|[0-9]?>>?[ \t]*/dev/null(?=[ \t\n|;&]|\Z)"
    r"|&>>?[ \t]*/dev/null(?=[ \t]*(?:[\n|;&]|\Z)))"
)
# The words of bash and zsh that open, join or close a command rather than
# name a program, and the modifiers that run the command after them (#2002).
# In `{ 2>&1; }`, `! 2>&1` or `do 2>&1`, the command after such a word holds
# redirections alone, which zsh runs as `$NULLCMD`. So a segment left with
# only such words once a harmless redirection is removed keeps the command
# whole (`_without_harmless_redirections`).
_SHELL_KEYWORDS = frozenset(
    {
        "!", "{", "}", "[[", "]]", "if", "then", "elif", "else", "fi", "case",
        "esac", "for", "foreach", "select", "while", "until", "do", "done",
        "repeat", "function", "time", "coproc", "nocorrect", "noglob", "exec",
        "command", "builtin", "-",
    }
)
# What each untrusted character opens, for the reason `decide()` gives.
_UNTRUSTED_KIND = {
    "$": "expansion",
    "`": "backtick",
    "<": "redirection",
    ">": "redirection",
    "(": "substitution",
}
# Whitespace the shell reads as part of a word, though Python's `str.split()`
# splits on it: anything but a space, a tab or a newline, such as a carriage
# return or a no-break space (#1942). `gh<no-break space>pr list` runs a
# program named `gh pr`, not `gh`, so a command holding one is not trusted.
_ODD_SPACE = re.compile(r"[^\S \t\n]")
# An operand of `export` the core can read: a plain `NAME`, or `NAME=value` /
# `NAME+=value`, its name written unquoted (#1942). The shell expands any other
# word before `export` reads it, so `export PAT?=bin` sets `PATH` where a file
# named `PATH=bin` lies in the directory.
_EXPORT_OPERAND = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\+?=|[ \t]*$)")
# An assignment to a variable that changes which program runs, or the code
# loaded into it before its own (#1942): the shell's search path (`PATH`, and
# zsh's `path`) and any other search path, such as `LD_LIBRARY_PATH`,
# `GIT_EXEC_PATH` or `PYTHONPATH`; the dynamic loader's `LD_*` and `DYLD_*`;
# the startup files a shell reads first (`BASH_ENV`, `ENV`, `ZDOTDIR`); zsh's
# `NULLCMD` and `READNULLCMD`, which name the program a command of
# redirections alone runs (#2002); and the variables of the interpreters and
# runtimes that run programs, Python's, Perl's, Ruby's, Node's and Java's
# options, which load code ahead of the program's own. `PATH=/tmp/x gh pr list`
# runs whichever `gh` the new path finds first. The list names a family of
# variables and cannot be complete: a variable outside it that changes which
# program runs is a hole on the allow side, to be added here when found. The
# program's own settings, such as `GIT_PAGER`, are not here: what a granted
# program is told to run is the grant's breadth, as a pager set in git's
# configuration file is.
_PROGRAM_VAR = re.compile(
    r"^(?:[A-Za-z0-9_]*(?:PATH|path)|LD_[A-Za-z0-9_]*|DYLD_[A-Za-z0-9_]*"
    r"|BASH_ENV|ENV|ZDOTDIR|NULLCMD|READNULLCMD|PYTHON[A-Za-z0-9_]*|PERL[A-Za-z0-9_]*"
    r"|RUBY[A-Za-z0-9_]*|NODE_OPTIONS|JAVA_TOOL_OPTIONS|_JAVA_OPTIONS"
    r"|JDK_JAVA_OPTIONS)\+?="
)
# A leading assignment written with a quote or a backslash (#1942). The core
# never matches an assignment's value, so removing its quotes makes no match
# more accurate: only a quoted argument is matched as the shell passes it on.
# So such an assignment keeps every grant from allowing, and a deny behind it
# still binds.
_QUOTED = re.compile(r"""['"\\]""")
# A bare `cd <path>` first segment: literally `cd` then exactly one path token
# with no shell metacharacter and not a flag. The token is intentionally
# restrictive — the moment it carries anything the splitter can't trust, we do
# not strip. Only a space or a tab parts `cd` from its path (#1942): after a
# newline the shell runs the next word as a command of its own, as it runs
# `{rm,-rf,~}` in `cd`, a newline, then `{rm,-rf,~};git status`, and inside
# any other whitespace it reads one word.
_BARE_CD = re.compile(r"""^cd[ \t]+([^\s'"`$<>|&;()]+)$""")
# A program name a reason may show (#1908): letters, digits and `.`, `_`, `+`,
# `-` only, so never a path, an assignment or a quoted fragment.
_BARE_WORD = re.compile(r"^[A-Za-z0-9._+-]+$")
# A character that makes a word a pathname pattern, which the shell expands to
# the names of files before the program sees it (#1960): `*`, `?` and `[` in
# every shell, and `^`, `#` and `~` under zsh's EXTENDED_GLOB. It counts only
# outside quotes and not after a backslash (`_globbed()`).
_GLOB = re.compile(r"[*?\[^#~]")
# The first characters of a pathname pattern that may expand to a word opening
# with `-` or `+`, a flag or a refspec that forces its ref (#1960): the `-` or
# `+` itself, or a glob character that may match it.
_FLAG_OPENERS = "-+*?[^"
# A bundle of short flags, such as `-uf`, which a program reads as `-u -f`
# (#1960).
_BUNDLE = re.compile(r"^-[A-Za-z0-9]{2,}$")
# An assignment to a variable that changes which configuration a program reads,
# which may set a forced refspec or an alias (#1960): `HOME` and the XDG base
# directories, any name holding `CONFIG`, such as `GIT_CONFIG_GLOBAL`,
# `GIT_CONFIG_COUNT` or `GH_CONFIG_DIR`, and git's repository directories. The
# list names a family of variables and cannot be complete.
_CONFIG_VAR = re.compile(
    r"^(?:HOME|XDG_[A-Za-z0-9_]*|[A-Za-z0-9_]*(?i:config)[A-Za-z0-9_]*"
    r"|GIT_DIR|GIT_COMMON_DIR)\+?="
)
# The program a recognizer's `pattern` names, where it opens with one plainly,
# such as `rm` in `^rm(?=\s)…`, `gh` in `^gh\s+…` or `git` in `^git push…`
# (#1960), as `projection._pattern_command` reads one. A pattern that names
# none may match any program.
_PATTERN_PROGRAM = re.compile(
    r"^\^([A-Za-z0-9._+-]+)(?=\\s|\(\?=\\s|\(\\s|\(\?:\\s|\\b|\s|$)"
)
# What keeps a deny from telling a form, for the reason `decide()` gives.
_UNSEEN_KIND = {
    "glob": "a pathname pattern",
    "config": "an assignment to a variable that changes the program's configuration",
    "options": "more options before a subcommand than the core reads",
    "git-config": "configuration the command sets or writes",
    "runner": "a command a runner runs that the core cannot read",
}
# The splitter that finds what a runner runs (#1990, ADR-025 point 5): `_SEP`,
# save that a `;` behind a backslash, where whitespace or the start of the
# command stands before that backslash, is no separator. The shell passes such
# a `\;` on as the word `;`, as find's terminator in `find . -exec rm {} \;`.
# Nothing quotes a backslash that whitespace stands before, and inside quotes a
# `;` is a word anyway. The denies still read each segment `_SEP` yields, so
# this only adds what a runner runs across a `\;`.
_RUN_SEP = re.compile(r"\s*(?:&&|\|\||\||(?<![ \t\n]\\)(?<!\A\\);|&|\n)\s*")
# The runners whose command a deny reads (#1990, ADR-025 point 5), with the
# options of each that the core knows, as GNU's, BSD's and the shells' read
# them. Each holds, in turn:
# - the short options that take no value, `-` among them where a lone `-` is
#   one, as `env -` is `env -i`
# - those that take a value, in the rest of their word or the next word
# - those that take a value only in the rest of their word, as GNU xargs's `-i`
# - the long options that take no value, or one only after `=`
# - those that take a value, after `=` or in the next word
# Any other option keeps the core from reading what the runner runs. `uv run`,
# find's `-exec`, and a shell given `-c` are read on their own terms.
_RUNNERS = {
    "env": (
        "-iv0", "uCPLU", "",
        frozenset({"ignore-environment", "null", "debug", "list-signal-handling",
                   "block-signal", "default-signal", "ignore-signal"}),
        frozenset({"unset", "chdir"}),
    ),
    "command": ("pvV", "", "", frozenset(), frozenset()),
    "exec": ("cl", "a", "", frozenset(), frozenset()),
    "nice": ("0123456789", "n", "", frozenset(), frozenset({"adjustment"})),
    "nohup": ("", "", "", frozenset(), frozenset()),
    "timeout": (
        "v", "sk", "",
        frozenset({"preserve-status", "foreground", "verbose"}),
        frozenset({"signal", "kill-after"}),
    ),
    "time": (
        "pvaqlh", "of", "",
        frozenset({"portability", "verbose", "append", "quiet"}),
        frozenset({"output", "format"}),
    ),
    "xargs": (
        "0rtpxo", "ILnPsEdaJRS", "ile",
        frozenset({"null", "no-run-if-empty", "verbose", "interactive", "exit", "open-tty",
                   "show-limits", "replace", "max-lines", "eof"}),
        frozenset({"arg-file", "delimiter", "max-args", "max-procs", "max-chars",
                   "process-slot-var"}),
    ),
}
# uv's own options and `uv run`'s, as clap reads them: the same five parts as
# `_RUNNERS` holds. uv is a runner only through its `run` subcommand.
_UV_OPTIONS = (
    "msUnqvhV", "wifPCp", "",
    frozenset({
        "all-extras", "no-dev", "only-dev", "dev", "no-default-groups", "all-groups", "module",
        "no-editable", "exact", "no-env-file", "isolated", "active", "no-active", "no-sync",
        "locked", "frozen", "script", "gui-script", "all-packages", "no-project", "no-index",
        "upgrade", "no-sources", "reinstall", "compile-bytecode", "no-build-isolation",
        "no-build", "no-binary", "no-cache", "refresh", "managed-python", "no-managed-python",
        "no-python-downloads", "quiet", "verbose", "system-certs", "native-tls", "offline",
        "no-progress", "no-config", "help", "version", "preview", "no-preview",
    }),
    frozenset({
        "extra", "no-extra", "group", "no-group", "only-group", "no-editable-package",
        "env-file", "with", "with-editable", "with-requirements", "package", "python-platform",
        "index", "default-index", "index-url", "extra-index-url", "find-links",
        "index-strategy", "keyring-provider", "upgrade-package", "upgrade-group", "resolution",
        "prerelease", "prerelease-package", "fork-strategy", "exclude-newer",
        "exclude-newer-package", "no-sources-package", "reinstall-package", "link-mode",
        "config-setting", "config-settings-package", "no-build-isolation-package",
        "no-build-package", "no-binary-package", "cache-dir", "refresh-package", "python",
        "color", "allow-insecure-host", "directory", "project", "config-file",
        "python-preference", "preview-features",
    }),
)
# The shells whose `-c` script a deny reads, one level deep.
_SHELLS = frozenset({"sh", "bash", "zsh", "dash"})
# find's actions that run a command.
_FIND_RUNS = ("-exec", "-execdir", "-ok", "-okdir")
# How many runners, one behind another, the core reads in a segment. Past them
# it cannot tell, so a crafted chain never stalls the hook.
_RUNNER_HOPS = 8
# A key of git's configuration that may set an alias or a forced push (#1990):
# an alias, a remote's push refspec or mirror flag, and an include, which may
# pull in any of them. Section and key names are read in any case, as git
# reads them.
_GIT_CONFIG_KEY = re.compile(r"alias\.|include|remote\..*\.(?:push|mirror)$", re.IGNORECASE)
# fmt: on


# ---- command segmentation + recognizer matcher ----------------------------


# The verdict path; the formatter leaves it alone (see the note after the imports).
# fmt: off
def _words(text: str) -> list[tuple[str, str]] | None:
    """The words of one segment as the shell reads them, each as (its text as
    written, the word the shell passes on), or None where the core cannot read
    them so (#1942).

    Words split at spaces and tabs, and quotes and backslashes are removed as
    the shell removes them, by the standard library's POSIX quoting rules. That
    is a tokenizer of words, not a parser of the shell's grammar (ADR-025
    point 3): the splitter still finds the segments, and the constructs these
    rules read otherwise than the shell does are untrusted before any word
    counts (`_UNTRUSTED`, `_ODD_SPACE`). None where a quote or a backslash does
    not close, as where the splitter cut a quoted `;`: the shell reads that
    text otherwise than the splitter does."""
    lexer = shlex.shlex(text, posix=True)
    lexer.whitespace = " \t"
    lexer.whitespace_split = True
    lexer.commenters = ""
    words: list[tuple[str, str]] = []
    start = 0
    try:
        while True:
            word = lexer.get_token()
            if word is None:
                return words
            end = lexer.instream.tell()
            words.append((text[start:end].lstrip(" \t"), word))
            start = end
    except ValueError:
        return None


def _segment_words(raw: str) -> list[tuple[str, str]]:
    """`_words()` of one segment, or, where the core cannot read them, the
    segment split at whitespace with each word as written, so a deny on it
    still binds. `decide()` never allows such a segment (`_doubts()`)."""
    words = _words(raw)
    return words if words is not None else [(tok, tok) for tok in raw.split()]


def _without_harmless_redirections(command: str) -> str:
    """`command` with each redirection that writes no file removed: an fd
    duplicated or closed, or output discarded to `/dev/null`
    (`_HARMLESS_REDIRECTION`, #2002). The whitespace around each stays, so
    the words left are read as before. The core then splits the rest, finds
    every other doubt in it, and matches each grant and deny on it.

    One pass over the command as written. Where the removal itself leaves a
    form that a second pass would remove, as in `> 2>&1 /dev/null`, which
    the shell rejects, the command is returned whole, so each of its
    redirections stays untrusted. So reading the result again changes
    nothing.

    The command is returned whole too where a removal leaves its segment with
    no program, as in `git status | 2>&1`, `X=1 >/dev/null` or `{ 2>&1; }`.
    zsh runs a command of redirections and assignments alone as `$NULLCMD`, a
    program the core never sees, and a word such as `{` or `do` opens a
    command of its own (`_SHELL_KEYWORDS`). A NUL in the command, which the
    removal marks its places with, keeps it whole as well."""
    if "\0" in command:
        return command
    marked = _HARMLESS_REDIRECTION.sub("\0", command)
    once = marked.replace("\0", "")
    if _HARMLESS_REDIRECTION.sub("", once) != once:
        return command
    for raw in _SEP.split(marked.strip()):
        if "\0" in raw:
            words = _segment_words(raw.replace("\0", ""))
            if all(word in _SHELL_KEYWORDS for _, word in words[_assignments(words):]):
                return command
    return once


def _assignments(words: list[tuple[str, str]]) -> int:
    """How many words at the front of a segment are assignments. An assignment
    is one where its name is written unquoted, as the shell reads it, so
    `"X=1" gh` runs a program named `X=1`.

    A segment led by `export` runs no program (#1942): `export` takes every
    word after it as a name or an assignment, so `export git PATH=/tmp/x`
    sets `PATH` and runs no `git`. All its words count, and no grant on a
    program covers it. The other builtins that assign, such as `declare`,
    `typeset`, `readonly` and `local`, stay the program a segment names, so
    the segment is left uncovered while no grant names them."""
    if words and words[0][1] == "export":
        return len(words)
    count = 0
    for text, _ in words:
        if not _ENVVAR.match(text):
            break
        count += 1
    return count


def segments(command: str) -> list[list[str]]:
    """Split a compound command into segments, each tokenized, with env-var
    prefixes (and a leading `export`) stripped. Fixes the `export X=1 && gh …`
    false-prompt that the flat settings matcher couldn't catch.

    Each word is the word the shell passes on, with its quotes and backslashes
    removed (#1942), so a grant or a deny matches `"--force"` as `--force`.

    A segment that only assigns is not dropped where a token of it holds an
    untrusted construct, such as `X=$(./x.sh)` (#1917): the value may run a
    command, so the segment stays whole, and no grant covers it. Where a command
    follows the assignments, they are stripped as before, so a deny on that
    command still binds, as on `X=$(true) rm -rf ~`.

    A redirection that writes no file, such as `2>&1` or `>/dev/null`, is
    removed before the split (#2002), so `uv run pytest 2>&1 | tail` is the
    segments `uv run pytest` and `tail`."""
    out: list[list[str]] = []
    for raw in _SEP.split(_without_harmless_redirections(command).strip()):
        words = _segment_words(raw)
        rest = words[_assignments(words):]
        if rest:
            out.append([word for _, word in rest])
        elif any(_UNTRUSTED.search(text) for text, _ in words):
            out.append([word for _, word in words])
    return out


def _brace_expansion(text: str) -> bool:
    """May the shell turn this word into several, by a brace expansion such as
    `{a,b}` or `{1..3}` (#1942)? `git push origin {main,--force}` runs
    `git push origin main --force`. True where a `{` has a `}` after it and a
    `,` or `..` after it, nested or not. The scan ignores quoting, so a quoted
    brace with a comma in it is not trusted either. It is a plain search of the
    word, linear in its length, so no word makes the hook stall."""
    start = text.find("{")
    if start < 0 or text.find("}", start) < 0:
        return False
    rest = text[start:]
    return "," in rest or ".." in rest


def _doubts(command: str) -> list[str]:
    """The kinds of construct in a Bash command that keep the core from reading
    its words, or the program it runs, as the shell does: empty when there is
    none (ADR-025 point 2). Each kind is a fixed phrase, never the command's
    text, since `decide()` gives them in its reason.

    A redirection that writes no file is no such construct (#2002): it is
    removed first, and every doubt is found in the rest exactly as before."""
    command = _without_harmless_redirections(command)
    kinds = {_UNTRUSTED_KIND[char] for char in _UNTRUSTED.findall(command)}
    if _ODD_SPACE.search(command):
        kinds.add("whitespace other than a space or a tab")
    for raw in _SEP.split(command.strip()):
        words = _words(raw)
        if words is None:
            kinds.add("unclosed quote")
            continue
        if any(text.startswith("#") for text, _ in words):
            kinds.add("comment")
        if any(_brace_expansion(text) for text, _ in words):
            kinds.add("brace expansion")
        count = _assignments(words)
        leading = [text for text, word in words[:count] if word != "export"]
        if any(_PROGRAM_VAR.match(text) for text in leading):
            kinds.add("assignment to PATH or another variable that picks the program")
        if any(_QUOTED.search(text) for text in leading):
            kinds.add("assignment written with a quote or a backslash")
        if words and words[0][1] == "export" and not all(
            _EXPORT_OPERAND.match(text) for text in leading
        ):
            kinds.add("export of a word the shell expands")
        # A program word holding whitespace, such as `'make test/x'`: a
        # recognizer's `pattern` reads the words joined by spaces, so it would
        # read that one word as two (#1942).
        if count < len(words) and any(space in words[count][1] for space in " \t"):
            kinds.add("program name holding whitespace")
    return sorted(kinds)


def _strip_leading_cd(command: str) -> str | None:
    """If `command` is a compound whose FIRST segment is a bare `cd <path>`
    followed by `&&` / `;`, return the remainder (everything after that first
    separator). Otherwise return None — meaning "do not strip; fall through to
    existing behaviour" (ADR-025 Phase 1).

    Mirrors the leading-`export` / `VAR=` strip in `segments()` in spirit, but
    operates on the raw command string (the cwd-change has no privilege of its
    own to recognise) and is deliberately conservative: it strips ONLY a bare
    `cd` with a single path arg carrying no shell metacharacter. A `cd` with a
    quote, `$()`, backtick, redirection, a flag, or more than one arg is NOT a
    bare `cd`, so we return None and let the unchanged path decide — never a
    silent strip of something the dumb splitter can't trust.
    """
    parts = _CD_SEP.split(command.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    first, remainder = parts
    if not _BARE_CD.match(first.strip()):
        return None
    remainder = remainder.strip()
    return remainder or None


def _matches_bash(rule: dict[str, Any], toks: list[str]) -> bool:
    if "pattern" in rule:
        if re.search(rule["pattern"], " ".join(toks)):
            return True
        if "cmd" not in rule:
            return False
    if "cmd" in rule:
        if not toks or toks[0] != rule["cmd"]:
            return False
        if "subcommand" in rule:
            rest = [t for t in toks[1:] if not t.startswith("-")]
            if not rest or rest[0] not in rule["subcommand"]:
                return False
        if "flag_any" in rule:
            if not any(f in toks for f in rule["flag_any"]):
                return False
        if "word_prefix_any" in rule:
            if not any(t.startswith(p) for t in toks[1:] for p in rule["word_prefix_any"]):
                return False
        return True
    return False


def _segment_privileges(privileges: dict[str, Any], toks: list[str]) -> set[str]:
    """Which privilege ids does one segment of a Bash command match? A request's
    privileges are the union over its segments, and `decide()` reads them one
    segment at a time to check that a grant covers each (ADR-025 point 2)."""
    return {
        name
        for name, spec in privileges.items()
        if any(_matches_bash(rule, toks) for rule in spec.get("recognize", {}).get("bash", []))
    }


# ---- the forms a deny holds against (#1960) --------------------------------
#
# A deny binds on the command it names in the forms programs read, not only in
# the form its recognizer spells (ADR-025 point 5): a short flag inside a
# bundle, a long flag cut to a prefix, with its value after `=` or behind one
# dash, a program named by its path or in other case, and a subcommand behind
# the options before it. Where a pathname pattern, or an assignment that
# changes the program's configuration, may make the command one a deny names,
# the core cannot tell, and defers rather than allows (ADR-025 point 2, from
# ADR-004 decision point 4). Only the denies read these forms: a grant still
# matches the command as written, so no form widens what a grant allows. Each
# reading errs toward the deny, which only narrows what runs unasked.


def _program_name(word: str) -> str:
    """The name of the program a word runs, in lower case: the last part of a
    path, such as `sudo` for `/usr/bin/sudo`, without the `=` zsh expands to
    the program's path. A case-insensitive file system, as macOS's is by
    default, runs `Git` as `git`."""
    return word.lstrip("=").rsplit("/", 1)[-1].lower()


def _flag_form(word: str, flags: list[str]) -> bool:
    """Is `word` a form of one of `flags`? The flag itself; a long flag with its
    value after `=`; a long flag cut to a prefix, as git and getopt read an
    unambiguous one; a long flag behind a single dash, as Go's flag package
    reads one; and a short flag inside a bundle, such as `-f` in `-uf`. A
    prefix of several long flags reads as each of them, and so does one that
    is itself another option of the program, such as `--proxy` for a denied
    `--proxy-insecure`: the reading errs toward the deny."""
    if word in flags:
        return True
    name = word.split("=", 1)[0]
    if name.startswith("--"):
        return len(name) > 2 and any(f.startswith(name) for f in flags if f.startswith("--"))
    if len(name) > 2 and name[0] == "-" and "-" + name in flags:
        return True
    if _BUNDLE.match(word):
        return any(len(f) == 2 and f[0] == "-" and f[1] in word[1:] for f in flags)
    return False


def _subcommand_candidates(rest: list[tuple[str, str]]) -> list[int]:
    """Where a program's subcommand may stand among the words after it: the
    first word that is no flag, and, while each such word follows a flag that
    may take it as its value, the next one too. `git -C . push` runs `push`."""
    found: list[int] = []
    after_flag = False
    for index, (_, word) in enumerate(rest):
        if word.startswith("-"):
            after_flag = True
            continue
        found.append(index)
        if not after_flag:
            break
        after_flag = False
    return found


def _globbed(text: str) -> bool:
    """Is a word, as written, a pathname pattern: does it hold a glob character
    the shell expands, outside quotes and not after a backslash? A `~` counts
    only after the word's first character, where zsh's EXTENDED_GLOB reads it;
    a word opening with one is a home directory."""
    quote = ""
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
        elif quote:
            if char == quote:
                quote = ""
            elif char == "\\" and quote == '"':
                escaped = True
        elif char == "\\":
            escaped = True
        elif char in "'\"":
            quote = char
        elif _GLOB.match(char) and (char != "~" or index > 0):
            return True
    return False


def _glob_head(word: str) -> str:
    """What every word a pathname pattern expands to opens with: the text
    before its first glob character. Nothing where it holds a `#`, which zsh's
    EXTENDED_GLOB reads as making the character before it optional."""
    return "" if "#" in word else _GLOB.split(word, maxsplit=1)[0]


def _may_open_flag(text: str, word: str) -> bool:
    """May this word reach the program as one opening with `-` or `+`? Only a
    pathname pattern, which the shell expands, and only where its first
    character is `-`, `+` or a glob character that may match one, or where
    it holds a `#` (`_glob_head`)."""
    return bool(word) and (word[0] in _FLAG_OPENERS or "#" in word) and _globbed(text)


def _structured_form(
    rule: dict[str, Any], words: list[tuple[str, str]], configured: bool
) -> str | None:
    """How a structured recognizer (`cmd`, `subcommand`, `flag_any`,
    `word_prefix_any`) reads one segment for a deny: "sure" where the segment
    is one of its forms, "glob" or "config" where a pathname pattern or a
    configuration assignment may make it one, None otherwise."""
    (first, program), rest = words[0], words[1:]
    if _globbed(first):
        return "glob"
    if _program_name(program) != rule["cmd"].lower():
        return None
    sub_sure = sub_maybe = flag_sure = flag_maybe = prefix_sure = prefix_maybe = True
    if "subcommand" in rule:
        places = [rest[i] for i in _subcommand_candidates(rest)]
        sub_sure = any(w in rule["subcommand"] for t, w in places if not _globbed(t))
        sub_maybe = sub_sure or any(_globbed(t) for t, _ in places)
    if "flag_any" in rule:
        flags = rule["flag_any"]
        flag_sure = any(_flag_form(w, flags) for t, w in rest if not _globbed(t))
        flag_maybe = flag_sure or any(_may_open_flag(t, w) for t, w in rest)
    if "word_prefix_any" in rule:
        # Every word a pathname pattern expands to opens with its head
        # (`_glob_head`): where the head opens with a prefix, the word does,
        # and where the prefix opens with the head, the word may. A quoted
        # glob character the shell passes on as it is.
        prefixes = rule["word_prefix_any"]
        globs = [_glob_head(w) for t, w in rest if _globbed(t)]
        heads = globs + [w for t, w in rest if not _globbed(t)]
        prefix_sure = any(h.startswith(p) for h in heads for p in prefixes)
        prefix_maybe = prefix_sure or any(p.startswith(h) for h in globs for p in prefixes)
    if sub_sure and flag_sure and prefix_sure:
        return "sure"
    if configured:
        return "config"
    if sub_maybe and flag_maybe and prefix_maybe:
        return "glob"
    return None


def _pattern_form(pattern: str, words: list[tuple[str, str]], configured: bool) -> str | None:
    """How a recognizer's `pattern` reads one segment for a deny, as
    `_structured_form` does. The pattern is matched with the program named by
    its name, and with the options before each place the subcommand may stand
    left out. A pattern spells the words it names, and their forms with them,
    so a pathname pattern anywhere in the segment, or a configuration
    assignment in the command, keeps the core from telling, for the program
    the pattern names, or for any where it names none plainly."""
    (first, program), rest = words[0], words[1:]
    name = _program_name(program)
    toks = [w for _, w in rest]
    places = _subcommand_candidates(rest)
    # The first 64 places only: each is a search over the rest of the segment,
    # and a crafted run of options must not stall the hook. Past them the core
    # cannot tell, so it defers.
    for start in (0, *places[:64]):
        if re.search(pattern, " ".join([name, *toks[start:]])):
            return "sure"
    if _globbed(first):
        return "glob"
    named = _PATTERN_PROGRAM.match(pattern)
    if named and named.group(1).lower() != name:
        return None
    if configured:
        return "config"
    if any(_globbed(text) for text, _ in rest):
        return "glob"
    if len(places) > 64:
        return "options"
    return None


def _rule_form(rule: dict[str, Any], words: list[tuple[str, str]], configured: bool) -> str | None:
    """`_structured_form` or `_pattern_form` of one recognizer, as
    `_matches_bash` reads a rule: its `pattern`, or else its structured fields."""
    found = []
    if "pattern" in rule:
        found.append(_pattern_form(rule["pattern"], words, configured))
    if "cmd" in rule:
        found.append(_structured_form(rule, words, configured))
    if "sure" in found:
        return "sure"
    return next((form for form in found if form), None)


def _export_prefix(words: list[tuple[str, str]]) -> int:
    """How many words at the front of a segment run the `export` builtin:
    `export` itself, behind any `builtin` words, which run the builtin they
    name. 0 where the segment is not led so. Only the denies read
    `builtin export` so: no grant covers a segment it leads."""
    for index, (_, word) in enumerate(words):
        if word == "export":
            return index + 1
        if word != "builtin":
            return 0
    return 0


# ---- what a runner runs, and git's configuration (#1990) --------------------
#
# A deny is matched on the command a listed runner runs, as well as on the
# runner (ADR-025 point 5): `env`, `command`, `exec`, `nice`, `nohup`,
# `timeout`, `time`, `xargs`, `uv run`, find's `-exec`, `-execdir`, `-ok` and
# `-okdir`, and `sh`, `bash`, `zsh` or `dash` given `-c`, whose script is read
# again as a command, one level deep. Where the core cannot read what a runner
# runs, every deny may bind. Configuration a git command sets or writes keeps a
# deny on git from telling, as an assignment that changes its configuration
# does. Only the denies read these: a grant still matches the command as
# written, since reading a runner for a grant would widen what it allows.


def _expands(text: str) -> bool:
    """Does the shell turn this word, as written, into something the core
    cannot read: an expansion, a substitution or a redirection (`_UNTRUSTED`),
    a pathname pattern or a brace expansion? Where such a word stands among a
    runner's options or names its program, the core cannot read what the
    runner runs."""
    return bool(_UNTRUSTED.search(text)) or _globbed(text) or _brace_expansion(text)


def _skip_options(rest: list[tuple[str, str]], spec: tuple[Any, ...]) -> int | None:
    """Where a runner's command starts among the words after the runner: past
    the options `spec` names (`_RUNNERS`), as getopt reads them, up to the
    first word that is no option, or past `--`. None where an option is one
    the core does not know, or where a word the shell expands stands among the
    options or names the program."""
    short_flags, short_values, short_attached, long_flags, long_values = spec
    index = 0
    while index < len(rest):
        text, word = rest[index]
        if _expands(text):
            return None
        if word == "--":
            return index + 1
        if word == "-" and "-" in short_flags:
            index += 1
            continue
        if word.startswith("--"):
            name = word[2:].split("=", 1)[0]
            if name in long_values and "=" not in word:
                index += 1
                if index < len(rest) and _expands(rest[index][0]):
                    return None
            elif name not in long_flags and name not in long_values:
                return None
            index += 1
            continue
        if not word.startswith("-") or word == "-":
            return index
        for at, char in enumerate(word[1:], start=1):
            if char in short_values:
                if at == len(word) - 1:
                    index += 1
                    if index < len(rest) and _expands(rest[index][0]):
                        return None
                break
            if char in short_attached:
                break
            if char == "-" or char not in short_flags:
                return None
        index += 1
    return index


def _uv_command(
    rest: list[tuple[str, str]],
) -> tuple[list[list[tuple[str, str]]], str | None, bool]:
    """The command `uv run` runs, as `_runner_commands` gives it: past uv's own
    options, the `run` subcommand and its options. Nothing where uv runs no
    `run`. `--env-file` loads variables the core never sees, so it counts as
    an assignment that changes the program's configuration."""
    start = _skip_options(rest, _UV_OPTIONS)
    if start is None:
        return [], None, True
    if start >= len(rest) or rest[start][1] != "run":
        return [], None, False
    after = _skip_options(rest[start + 1 :], _UV_OPTIONS)
    if after is None:
        return [], None, True
    end = start + 1 + after
    given = any(word.split("=", 1)[0] == "--env-file" for _, word in rest[:end])
    return ([rest[end:]] if end < len(rest) else []), ("config" if given else None), False


def _may_name_a_find_action(word: str) -> bool:
    """May a pathname pattern of find's own expand to an action that runs a
    command (`_FIND_RUNS`)? Always where it holds a character zsh's
    EXTENDED_GLOB reads, which the standard library's matcher does not."""
    return any(char in word for char in "^#~") or any(
        fnmatch.fnmatchcase(action, word) for action in _FIND_RUNS
    )


def _find_commands(rest: list[tuple[str, str]]) -> tuple[list[list[tuple[str, str]]], bool]:
    """The commands find runs, each from after an action of `_FIND_RUNS` up to
    its `;`, or its `+` right behind `{}`, as GNU and BSD find end one. And
    whether a word of find's own may hide such an action: an expansion, a
    brace expansion, or a pathname pattern that may expand to one. A
    substitution or a redirection there hides none, so find's `\\(` is read."""
    commands: list[list[tuple[str, str]]] = []
    index = 0
    while index < len(rest):
        text, word = rest[index]
        if word in _FIND_RUNS:
            start = end = index + 1
            while end < len(rest):
                ender = rest[end][1]
                if ender == ";" or (ender == "+" and end > start and rest[end - 1][1] == "{}"):
                    break
                end += 1
            commands.append(rest[start:end])
            index = end + 1
            continue
        if "$" in text or "`" in text or _brace_expansion(text):
            return commands, True
        if _globbed(text) and _may_name_a_find_action(word):
            return commands, True
        index += 1
    return commands, False


def _shell_script(rest: list[tuple[str, str]]) -> tuple[bool, str | None]:
    """The script a shell given `-c` runs, from the words after the shell's
    name: the first word that is no option, where an option bundle holding
    `c` came before it. `-o` and `-O` take the next word, as `--rcfile` and
    `--init-file` do. Also whether the core cannot read it: a word the shell
    expands where an option may stand, or as the script itself. None where
    the shell is given no `-c`."""
    has_c = False
    index = 0
    while index < len(rest):
        text, word = rest[index]
        if word in ("--", "-"):
            index += 1
            break
        if not (len(word) > 1 and word[0] in "-+"):
            break
        if _expands(text):
            return True, None
        if word.startswith("--"):
            index += 2 if word in ("--rcfile", "--init-file") else 1
            continue
        has_c = has_c or (word[0] == "-" and "c" in word[1:])
        index += 2 if ("o" in word[1:] or "O" in word[1:]) else 1
    if index >= len(rest):
        return False, None
    text, word = rest[index]
    if not has_c:
        return _expands(text), None
    return _expands(text), word


def _runner_commands(
    name: str, rest: list[tuple[str, str]]
) -> tuple[list[list[tuple[str, str]]], str | None, bool]:
    """The commands the runner `name` runs, given the words after it; the
    configuration kind it hands them, "config" where `env` assigns, or `uv run`
    loads, a variable that changes it; and whether the core cannot read them.
    Nothing for a program that is no runner, and for a shell, whose `-c`
    script `_runner_parts` reads."""
    if name == "find":
        commands, unread = _find_commands(rest)
        return commands, None, unread
    if name == "uv":
        return _uv_command(rest)
    spec = _RUNNERS.get(name)
    if spec is None:
        return [], None, False
    index = _skip_options(rest, spec)
    if index is None:
        return [], None, True
    given = None
    if name == "env":
        # env reads every word holding `=` before its program as an
        # assignment, quoted or not.
        while index < len(rest) and "=" in rest[index][1]:
            if _expands(rest[index][0]):
                return [], None, True
            if _CONFIG_VAR.match(rest[index][1]):
                given = "config"
            index += 1
    if name == "timeout":
        # timeout's duration stands before its program.
        if index < len(rest) and _expands(rest[index][0]):
            return [], None, True
        index += 1
    return ([rest[index:]] if index < len(rest) else []), given, False


def _git_configures(words: list[tuple[str, str]]) -> str | None:
    """"git-config" where a git command sets configuration, which may hold an
    alias or a forced refspec (#1990, ADR-025 point 5): `-c` or `--config-env`
    before its subcommand, or `git config` naming a key `_GIT_CONFIG_KEY`
    matches. A word the shell expands where such an option or key may stand
    counts too. Configuration git reads from its files is the grant's breadth,
    and no such setting."""
    if not words or _program_name(words[0][1]) != "git":
        return None
    rest = words[1:]
    places = _subcommand_candidates(rest)
    for text, word in rest[: places[-1] if places else len(rest)]:
        if word == "-c" or word.startswith("--config-env"):
            return "git-config"
        if _may_open_flag(text, word) or _brace_expansion(text):
            return "git-config"
    for place in places:
        if rest[place][1] != "config":
            continue
        for text, word in rest[place + 1 :]:
            if _GIT_CONFIG_KEY.match(word) or _globbed(text) or _brace_expansion(text):
                return "git-config"
    return None


def _names_runner(words: list[tuple[str, str]]) -> bool:
    """Does a segment whose words the core cannot read name a runner? Its
    first word is read with its quotes and backslashes dropped."""
    name = _program_name(re.sub(r"[\"'\\]", "", words[0][0]))
    return name in _RUNNERS or name in _SHELLS or name in ("find", "uv")


def _runner_parts(
    words: list[tuple[str, str]], kind: str | None, depth: int
) -> tuple[list[tuple[list[tuple[str, str]], str | None]], bool]:
    """Each command the runner at the front of `words` runs, read through
    every runner behind it, with the configuration kind it carries; and
    whether the core cannot read one. A shell's `-c` script is split and read
    again as a command (`_deny_parts`), one level deep: a script at `depth` 1
    that runs another is deeper nesting. Past `_RUNNER_HOPS` runners the core
    cannot tell."""
    parts: list[tuple[list[tuple[str, str]], str | None]] = []
    opaque = False
    pending = [(words, kind)]
    hops = 0
    while pending:
        current, carried = pending.pop()
        hops += 1
        if hops > _RUNNER_HOPS:
            return parts, True
        name = _program_name(current[0][1])
        if name in _SHELLS:
            unread, script = _shell_script(current[1:])
            opaque = opaque or unread
            if script is not None and depth > 0:
                opaque = True
            elif script is not None:
                inner, inner_opaque = _deny_parts(script, depth + 1)
                parts.extend((found, found_kind or carried) for found, found_kind in inner)
                opaque = opaque or inner_opaque or bool(_doubts(script))
            continue
        commands, given, unread = _runner_commands(name, current[1:])
        opaque = opaque or unread
        for command in commands:
            if not command:
                continue
            if _expands(command[0][0]):
                opaque = True
                continue
            handed = carried or given
            parts.append((command, handed or _git_configures(command)))
            pending.append((command, handed))
    return parts, opaque


def _deny_parts(
    command: str, depth: int
) -> tuple[list[tuple[list[tuple[str, str]], str | None]], bool]:
    """The commands a deny reads in a Bash command, each with what keeps a
    deny on its program from telling its configuration ("config", "git-config"
    or None); and whether the core cannot read what a runner runs.

    Each segment `_SEP` yields is one, as the denies read it before #1990. So
    is each command a runner runs, found in the segments `_RUN_SEP` yields,
    which keep find's `\\;` in its segment. An assignment that changes the
    program's configuration counts where the shell hands it on: in front of a
    command, for that command, and in a segment that only assigns or exports,
    `builtin export` included, for the segments after it.

    It reads the command with each redirection that writes no file removed
    (#2002), so a program behind one, as in `2>/dev/null rm -rf ~`, is the
    program a deny reads."""
    cleaned = _without_harmless_redirections(command).strip()
    parts: list[tuple[list[tuple[str, str]], str | None]] = []
    opaque = False
    for splitter in (_SEP, _RUN_SEP):
        inherited: str | None = None
        for raw in splitter.split(cleaned):
            read = _words(raw)
            words = read if read is not None else [(tok, tok) for tok in raw.split()]
            exported = _export_prefix(words)
            count = len(words) if exported else _assignments(words)
            assigned = any(_CONFIG_VAR.match(text) for text, _ in words[exported:count])
            configured = "config" if assigned else None
            rest = words[count:]
            if not rest:
                inherited = inherited or configured
                continue
            kind = inherited or configured
            if splitter is _SEP:
                parts.append((rest, kind or _git_configures(rest)))
                continue
            behind, unread = _runner_parts(rest, kind, depth)
            parts.extend(behind)
            opaque = opaque or unread or (read is None and _names_runner(rest))
    return parts, opaque


def _deny_forms(
    catalog: dict[str, Any], request: dict[str, Any]
) -> tuple[set[str], dict[str, set[str]]]:
    """For the denies of a Bash request: the privileges it matches in a form
    the program reads, and those it may match in a form the core cannot see,
    each with what keeps the core from seeing it (the keys of `_UNSEEN_KIND`).

    It reads each command `_deny_parts` finds: each segment, and each command
    a listed runner runs (#1990). Where the core cannot read what a runner
    runs, every privilege a Bash recognizer names may bind unseen."""
    if request.get("type") != "bash":
        return set(), {}
    parts, opaque = _deny_parts(request.get("command", ""), 0)
    sure: set[str] = set()
    unsure: dict[str, set[str]] = {}
    for name, spec in catalog.get("privileges", {}).items():
        rules = spec.get("recognize", {}).get("bash", [])
        for rule in rules:
            for words, kind in parts:
                form = _rule_form(rule, words, kind is not None)
                if form == "sure":
                    sure.add(name)
                elif form:
                    unsure.setdefault(name, set()).add(kind if form == "config" and kind else form)
        if opaque and rules:
            unsure.setdefault(name, set()).add("runner")
    return sure, {name: kinds for name, kinds in unsure.items() if name not in sure}
# fmt: on


def recognized_privileges(catalog: dict[str, Any], request: dict[str, Any]) -> set[str]:
    """Which privilege ids does this request match?

    A file-tool request that names its target (`path`) and the project root
    (`root`) also matches the path-scoped privileges whose folder holds that
    target (the agent workspace); see `_path_scoped_privileges`."""
    privileges = catalog.get("privileges", {})
    hits: set[str] = set()
    if request.get("type") == "tool":
        tool = request.get("tool")
        for name, spec in privileges.items():
            if tool in spec.get("recognize", {}).get("tool", []):
                hits.add(name)
        hits |= _path_scoped_privileges(privileges, request)
    elif request.get("type") == "bash":
        for toks in segments(request.get("command", "")):
            hits |= _segment_privileges(privileges, toks)
    return hits


# ---- path-scoped allows: the agent workspace (#1043) ------------------------
#
# A privilege whose recognizer carries `path` is scoped to folders, each named
# relative to the root of a checkout of the project: the project root, or
# another working tree of the same repository (a subagent working in a linked
# worktree keeps its workspace at that worktree's root). It is recognized only
# for a FILE TOOL listed in `path.tools` whose target lies inside one of those
# folders — never for the tool alone, and never for a shell command: a redirect
# into the folder is judged like any other shell write (ADR-025, unchanged). So
# a grant of it neither reaches nor denies a file anywhere else. It reduces
# prompts on the allow side, keyed on the target path; it confines nothing —
# shell reach is the OS sandbox's (`filesystem-confinement`); the file tools
# run outside the sandbox, so inside the folder the recogniser's precision is
# the gate (ADR-060 point 6).
#
# The folder counts only as the checkout itself holds it: named relative and
# never climbing out with `..`, and reached through no symlink — a symlinked
# `.agent-workspace` would carry the grant to wherever it points. A repository
# or worktree nested inside the folder is not the folder: its tracked files are
# another checkout's. Nor is a file hard-linked from elsewhere, which a write
# through the folder's name would change at its other name.


def _target_path(tool_input: dict[str, Any]) -> Any:
    """The path a file tool names: `file_path` (Read, Write, Edit, MultiEdit)
    or `notebook_path` (NotebookEdit)."""
    return tool_input.get("file_path") or tool_input.get("notebook_path")


def _enclosing_checkout(start: str) -> str | None:
    """The nearest directory at or above `start` holding a `.git` entry."""
    current = start
    while True:
        if os.path.lexists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _git_pointer(checkout: str) -> str | None:
    """Where a linked worktree's `.git` file points (`gitdir: <dir>`), resolved;
    None when `checkout`'s `.git` is not such a file."""
    try:
        with open(os.path.join(checkout, ".git"), encoding="utf-8") as fh:
            pointer = fh.read().strip()
    except OSError:
        return None
    if not pointer.startswith("gitdir:"):
        return None
    return os.path.realpath(os.path.join(checkout, pointer[len("gitdir:") :].strip()))


def _common_git_dir(checkout: str) -> str | None:
    """The git directory every working tree of `checkout`'s repository shares —
    what `git rev-parse --git-common-dir` answers: its `.git` directory, or, for
    a linked worktree, the directory its own git directory's `commondir` names."""
    marker = os.path.join(checkout, ".git")
    if os.path.isdir(marker):
        return os.path.realpath(marker)
    gitdir = _git_pointer(checkout)
    if gitdir is None:
        return None
    try:
        with open(os.path.join(gitdir, "commondir"), encoding="utf-8") as fh:
            return os.path.realpath(os.path.join(gitdir, fh.read().strip()))
    except OSError:
        return gitdir


def _same_repository(holder: str, common: str) -> bool:
    """Is `holder` a working tree of the repository whose common git directory
    is `common`? The main one, whose `.git` is that directory; or a linked one
    git registered there — its `.git` points at `<common>/worktrees/<id>`, and
    that entry's `gitdir` file points back at it. A `.git` pointer planted
    anywhere else does not make a worktree."""
    marker = os.path.join(holder, ".git")
    if os.path.isdir(marker):
        return os.path.realpath(marker) == common
    gitdir = _git_pointer(holder)
    if gitdir is None or os.path.dirname(gitdir) != os.path.realpath(
        os.path.join(common, "worktrees")
    ):
        return False
    try:
        with open(os.path.join(gitdir, "gitdir"), encoding="utf-8") as fh:
            back = fh.read().strip()
    except OSError:
        return False
    return os.path.realpath(os.path.join(gitdir, back)) == os.path.realpath(marker)


def _checkouts(path: str, root: str) -> list[str]:
    """The checkouts whose folders `path` may lie in: the project root, and the
    working tree holding `path` when it is another one of the same repository.
    Another repository's never counts."""
    project = os.path.realpath(root)
    found = [project]
    holder = _enclosing_checkout(os.path.dirname(path))
    if holder is not None and holder != project:
        common = _common_git_dir(project)
        if common is not None and _same_repository(holder, common):
            found.append(holder)
    return found


def _folder_top(checkout: str, folder: Any) -> str | None:
    """`folder`'s path in `checkout` (a resolved directory), or None when the
    folder cannot be trusted there: not a relative name, climbing out with
    `..`, or reached through a symlink."""
    if not isinstance(folder, str) or not folder or os.path.isabs(folder) or folder.startswith("~"):
        return None
    if ".." in folder.split("/"):
        return None
    top = os.path.join(checkout, os.path.normpath(folder))
    return top if os.path.realpath(top) == top else None


def _nested_checkout(path: str, top: str) -> bool:
    """Does any directory from the folder `top` down to `path`'s parent hold a
    `.git` entry? Then `path` lies in a repository or worktree nested inside
    the folder — another checkout's files, not the folder's."""
    current = os.path.dirname(path)
    while True:
        if os.path.lexists(os.path.join(current, ".git")):
            return True
        parent = os.path.dirname(current)
        if current == top or parent == current:
            return False
        current = parent


def _inside(path: str, root: str, folders: list[Any]) -> bool:
    """Does the resolved `path` lie strictly inside one of `folders` of a
    checkout of the project at `root`, and in no repository or worktree nested
    inside that folder?"""
    for checkout in _checkouts(path, root):
        for folder in folders:
            top = _folder_top(checkout, folder)
            if top is None or path == top or os.path.commonpath([path, top]) != top:
                continue
            if not _nested_checkout(path, top):
                return True
    return False


def _hard_linked(path: str) -> bool:
    """Is `path` an existing file with more than one name? A write through one
    name changes the file at every other, wherever it lies."""
    try:
        info = os.stat(path)
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and info.st_nlink > 1


def _path_scoped_privileges(privileges: dict[str, Any], request: dict[str, Any]) -> set[str]:
    """The path-scoped privileges a file-tool request is recognized as: those
    listing its tool whose folder holds its target, symlinks resolved — a link
    out of the folder is outside it, and so is a file hard-linked from anywhere.
    Empty without a target or a project root."""
    target, root = request.get("path"), request.get("root")
    if not isinstance(target, str) or not target or not root:
        return set()
    path = os.path.realpath(os.path.join(request.get("cwd") or root, target))
    if _hard_linked(path):
        return set()
    hits: set[str] = set()
    for name, spec in privileges.items():
        scoped = spec.get("recognize", {}).get("path")
        if not isinstance(scoped, dict) or request.get("tool") not in (scoped.get("tools") or []):
            continue
        if _inside(path, root, scoped.get("folders") or []):
            hits.add(name)
    return hits


# ---- subjects, scope, decision ---------------------------------------------


# The verdict path; the formatter leaves it alone (see the note after the imports).
# fmt: off
def _privilege_ids(value: Any) -> set[str]:
    """Normalise a grant's `privilege` (token or list of tokens) to bare ids."""
    vals = value if isinstance(value, list) else [value]
    out: set[str] = set()
    for v in vals:
        m = _TOKEN.match(v) if isinstance(v, str) else None
        out.add(m.group(1) if m else v)
    return out


def _extract_host(url: str) -> str:
    """Extract the hostname from a URL string.  Returns an empty string if the
    URL cannot be parsed (no scheme, malformed, etc.) — a host that can never
    match a well-formed glob, so the grant is denied rather than silently passed.

    stdlib-only: uses urllib.parse which ships with every Python ≥ 3.6 and is
    safe inside macOS Seatbelt (ADR-014).
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.hostname or ""
    except Exception:
        return ""


def _scope_ok(
    scope: list[str] | None,
    cwd: str,
    *,
    scope_type: str | None = None,
    url: str | None = None,
) -> tuple[bool, str | None]:
    """Check whether a grant's scope constraint is satisfied.

    Returns (ok, rejection_reason_or_None).

    For ``directory``-scoped privileges (default for absent ``scope_type``):
      the grant's scope globs are matched against ``cwd`` via fnmatch.

    For ``domain``-scoped privileges (``scope_type="domain"``):
      positive allow-list semantics — the grant's scope globs are matched
      against the hostname extracted from ``url``.  Only matching hosts are
      allowed; non-matching hosts are blocked.

      Deny/negation scopes (any glob starting with ``!``) are explicitly
      unsupported and rejected with a clear reason rather than silently
      accepted.  Rationale: a tool-layer denylist is a false boundary — an
      agent's raw ``bash curl`` bypasses it at the agent-blind sandbox layer
      (ADR-004, Alternatives considered, "Relabel `network-egress` as
      natively enforced…").  Only positive allow-lists are honest at this
      layer.

    When ``scope`` is absent or empty the grant is unconstrained (anywhere).
    """
    if not scope:
        return True, None

    # Deny/negation scopes are explicitly unsupported for domain privileges.
    # Check upfront so the error message is clear regardless of scope_type.
    negation_globs = [pat for pat in scope if pat.startswith("!")]
    if negation_globs:
        return False, (
            f"deny/negation scopes are unsupported for domain-scoped privileges "
            f"({negation_globs!r}): a tool-layer denylist is a false boundary "
            f'(ADR-004, Alternatives considered, "Relabel `network-egress` as '
            f'natively enforced…"); use positive allow-list globs only'
        )

    if scope_type == "domain":
        host = _extract_host(url or "")
        if not host:
            return False, (
                f"domain-scope check failed: could not extract a hostname from "
                f"request URL {url!r}"
            )
        matched = any(fnmatch.fnmatch(host, pat) for pat in scope)
        if matched:
            return True, None
        return False, (
            f"domain-scope: host {host!r} does not match any allowed glob in "
            f"{scope!r}"
        )

    # directory scope (default)
    matched = any(
        fnmatch.fnmatch(cwd, pat) or fnmatch.fnmatch(cwd, pat.rstrip("*") + "*")
        for pat in scope
    )
    return matched, None


def _effective_grants(model: dict[str, Any], subject: str) -> list[dict[str, Any]]:
    keep = {"all", subject}
    return [g for g in model.get("grants", []) if g.get("subject") in keep]


def _uncovered_segments(
    catalog: dict[str, Any], request: dict[str, Any], allowed: set[str]
) -> list[list[str]]:
    """The segments of a Bash request that none of the `allowed` privileges
    covers: a segment that matches no privilege, or only privileges no allow
    grant of the subject reaches (ADR-025 point 2). Empty for a tool request,
    and for a Bash request whose every segment is covered."""
    if request.get("type") != "bash":
        return []
    privileges = catalog.get("privileges", {})
    return [
        toks
        for toks in segments(request.get("command", ""))
        if not _segment_privileges(privileges, toks) & allowed
    ]


def _named_behind_glob(rule: dict[str, Any], words: list[tuple[str, str]]) -> bool:
    """Does a pathname pattern that may expand to a word opening with `-` stand
    before the subcommand `rule` names, as `_matches_bash` finds it, or before
    the first of its flags the segment holds? Such a word may be an option
    that takes the next word as its value. Never for a rule naming neither."""
    toks = [word for _, word in words]
    limit = 0
    if "subcommand" in rule:
        limit = next((i for i, tok in enumerate(toks) if i and not tok.startswith("-")), 0)
    if "flag_any" in rule:
        flags = [i for i, tok in enumerate(toks) if tok in rule["flag_any"]]
        limit = max(limit, flags[0] if flags else 0)
    return any(_may_open_flag(text, word) for text, word in words[1:limit])


def _glob_widened(
    catalog: dict[str, Any], request: dict[str, Any], allowed: set[str]
) -> list[list[str]]:
    """The segments of a Bash request that the `allowed` privileges cover only
    through a recognizer naming a subcommand or flags, behind a pathname
    pattern that may expand to a word opening with `-` (#1990, ADR-025 point
    2). The subcommand or flag the grant names may then be an option's value,
    so the command may not be the one the grant names. A grant naming only
    the program still matches a pathname pattern as written."""
    if request.get("type") != "bash":
        return []
    privileges = catalog.get("privileges", {})
    widened: list[list[str]] = []
    for raw in _SEP.split(_without_harmless_redirections(request.get("command", "")).strip()):
        words = _segment_words(raw)
        words = words[_assignments(words):]
        if not words:
            continue
        toks = [word for _, word in words]
        rules = [
            rule
            for name in sorted(allowed)
            for rule in privileges.get(name, {}).get("recognize", {}).get("bash", [])
            if _matches_bash(rule, toks)
        ]
        if rules and all(_named_behind_glob(rule, words) for rule in rules):
            widened.append(toks)
    return widened


def _shown_program(toks: list[str]) -> str:
    """How a reason names an uncovered segment: its program when that is a bare
    word, such as `sh` or `python3`, and `<other>` otherwise. A path, an
    assignment or any other token may carry data, and the diagnostic log
    records the reason beside a command it redacts on spaces alone."""
    return toks[0] if _BARE_WORD.match(toks[0]) else "<other>"


def decide(
    model: dict[str, Any],
    catalog: dict[str, Any],
    request: dict[str, Any],
    posture: str | None = None,
) -> tuple[str, str]:
    """Decide a request: returns (decision, reason), decision in
    {allow, deny, abstain}. `abstain` defers to the harness's normal flow
    (lenient); strict maps an unmodeled request to deny.

    `request` = {type: "bash"|"tool", command|tool, cwd, subject[, url]}.
    The optional `url` field carries the request URL for ``domain``-scoped
    privilege checks (web-fetch).  Effective grants = baseline (`all`) ∪ the
    subject's own grants; deny wins; a scoped allow denies the privilege
    outside its scope.  A compound Bash command is allowed only when an allow
    covers every segment of it, and a Bash command holding a construct the
    splitter cannot trust never is (ADR-025 point 2).

    Scope semantics by privilege ``scope_type`` (from the catalog):
      - ``directory`` (default): grant scope globs are matched against ``cwd``.
      - ``domain``: grant scope globs are matched against the URL hostname
        (positive allow-list; deny/negation globs are explicitly rejected).
    """
    posture = posture or model.get("posture", "lenient")
    subject = request["subject"]

    # Leading-`cd` strip (ADR-025 Phase 1). When a bash command's first segment
    # is a bare `cd <path> &&` / `cd <path> ;`, drop it and decide on the
    # remainder against the unchanged grant model — `cd src && gh pr list`
    # auto-approves exactly as `gh pr list` would. It strips ONLY a bare `cd`
    # (`_strip_leading_cd` returns None otherwise, so a tricky
    # `cd "/x; rm -rf ~" && …` falls through to the full-command path, where it
    # is decided whole and at worst abstains — never silently allowed). The
    # remainder is decided like any command, so the check for an untrusted
    # construct below covers it as it covers a command with no `cd` (#1917).
    # A command holding such a construct anywhere, its `cd` included, is not
    # stripped at all (#1942): it is decided whole, where every deny still
    # binds on each segment and the construct then keeps every grant from
    # allowing, so a `cd` whose word the shell reads otherwise, such as
    # `cd {a,b}`, never hides what it runs.
    # The remainder is decided at the ORIGINAL cwd: stripping `cd` can never
    # grant a directory-scoped privilege the un-stripped command lacked.
    # A redirection that writes no file is removed first, as every reading of
    # the command removes it (#2002), so `cd /x 2>/dev/null && git status`
    # strips its `cd` as `cd /x && git status` does.
    if request.get("type") == "bash" and not _doubts(request.get("command", "")):
        remainder = _strip_leading_cd(
            _without_harmless_redirections(request.get("command", ""))
        )
        if remainder is not None:
            return decide(model, catalog, {**request, "command": remainder}, posture)

    hits = recognized_privileges(catalog, request)
    # A deny binds on the forms of the command it names (ADR-025 point 5), and
    # where a form may be one the core cannot see, the deny keeps every grant
    # from allowing (#1960, ADR-025 point 2). A grant still matches the command
    # as written.
    forms, unseen = _deny_forms(catalog, request)
    privileges_catalog = catalog.get("privileges", {})
    allowed: set[str] = set()
    undecided: set[str] = set()
    for g in _effective_grants(model, subject):
        privs = _privilege_ids(g.get("privilege"))
        if g.get("effect", "allow") == "deny":
            overlap = (hits | forms) & privs
            if overlap:
                return "deny", f"deny grant for {subject} on {sorted(overlap)}"
            undecided |= set(unseen) & privs
            continue
        overlap = hits & privs
        if not overlap:
            continue
        # Determine scope_type from the catalog for the overlapping privileges.
        # When the overlap spans multiple privileges, use the most restrictive
        # scope_type: prefer "domain" > "directory" > None.  In practice a
        # single grant rarely covers privileges of mixed scope_type.
        scope_type: str | None = None
        for pid in overlap:
            pspec = privileges_catalog.get(pid, {})
            st = pspec.get("scope_type")
            if st == "domain":
                scope_type = "domain"
                break
            if st == "directory":
                scope_type = "directory"
        ok, reason = _scope_ok(
            g.get("scope"),
            request.get("cwd", ""),
            scope_type=scope_type,
            url=request.get("url"),
        )
        if ok:
            allowed |= overlap
        else:
            deny_msg = reason or (
                f"{sorted(overlap)} allowed for {subject} only in "
                f"{g.get('scope')}, not {request.get('cwd')!r}"
            )
            return "deny", deny_msg
    # A construct the dumb splitter cannot be trusted on, anywhere in a Bash
    # command, keeps every grant from allowing it (#1917, ADR-025 point 2 from
    # ADR-004 decision point 4): the segments the splitter yields may not be the
    # commands the shell runs. So does a word the core cannot read as the shell
    # does, or an assignment that changes which program runs (#1942): the
    # words matched may not be the words the shell passes on, or the program
    # not the one the grant names. It is checked after the grants, so a deny
    # still wins. The reason lists the kinds of construct, never the command's
    # text.
    doubts = _doubts(request.get("command", "")) if request.get("type") == "bash" else []
    if doubts:
        kinds = " / ".join(doubts)
        if posture == "strict":
            return "deny", f"strict posture: an untrusted construct ({kinds}) in the command"
        return "abstain", (
            f"an untrusted construct ({kinds}) in the command — fail closed, "
            f"defer to the harness's normal flow"
        )
    # A deny that may bind on a form the core cannot see keeps every grant from
    # allowing (#1960): a pathname pattern may expand to a flag the deny names,
    # and a configuration may set one. The reason names the privileges and the
    # kinds of form, never the command's text.
    if undecided:
        kinds = " / ".join(
            sorted({_UNSEEN_KIND[kind] for name in undecided for kind in unseen[name]})
        )
        if posture == "strict":
            return "deny", (
                f"strict posture: a deny on {sorted(undecided)} may bind on what the "
                f"shell runs ({kinds})"
            )
        return "abstain", (
            f"a deny on {sorted(undecided)} may bind on what the shell runs ({kinds}) "
            f"— fail closed, defer to the harness's normal flow"
        )
    if allowed:
        # A grant on one segment of a compound never carries another (#1908):
        # every segment the splitter yields must match a privilege an allow
        # covers, or the core does not allow (ADR-025 point 2). The reason
        # names only each uncovered segment's program, never its arguments,
        # which may hold a path or a secret the diagnostic log redacts.
        uncovered = _uncovered_segments(catalog, request, allowed)
        # A pathname pattern that may expand to an option, before the
        # subcommand or flag a grant names, keeps that grant from allowing
        # (#1990, ADR-025 point 2). The reason names the program alone.
        widened = [] if uncovered else _glob_widened(catalog, request, allowed)
        if widened:
            programs = sorted({_shown_program(toks) for toks in widened})
            if posture == "strict":
                return "deny", (
                    f"strict posture: a pathname pattern may expand to an option "
                    f"the grant on the {programs} segment(s) does not name"
                )
            return "abstain", (
                f"a pathname pattern may expand to an option the grant on the "
                f"{programs} segment(s) does not name — fail closed, defer to the "
                f"harness's normal flow"
            )
        if not uncovered:
            return "allow", f"allow grant for {subject} on {sorted(hits)}"
        programs = sorted({_shown_program(toks) for toks in uncovered})
        if posture == "strict":
            return "deny", (
                f"strict posture: no grant covers the {programs} segment(s) "
                f"of this compound"
            )
        return "abstain", (
            f"no grant covers the {programs} segment(s) of this compound — "
            f"fail closed, defer to the harness's normal flow"
        )
    if posture == "strict":
        return "deny", "strict posture: nothing grants this request"
    return "abstain", "lenient posture: defer to the harness's normal flow"


def _read_default_agent(project_root: str) -> str | None:
    """Read the configured default agent from .claude/settings.json.

    Returns the value of the top-level ``agent`` key if present and non-empty,
    otherwise ``None``.  Uses stdlib ``json`` only (the hook runs bare python3 —
    no third-party deps).  Any I/O or parse error silently returns ``None`` so
    the caller falls back to ``operator`` — never throw from subject resolution.
    """
    import json as _json
    import os.path as _osp

    path = _osp.join(project_root, ".claude", "settings.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = _json.load(fh)
        agent = data.get("agent")
        return str(agent) if agent and isinstance(agent, str) else None
    except Exception:
        return None
# fmt: on


def hook_decide(
    model: dict[str, Any],
    catalog: dict[str, Any],
    payload: dict[str, Any],
    project_root: str | None = None,
    *,
    as_subject: str | None = None,
) -> tuple[str, str]:
    """Decision-core entry point for a PreToolUse hook payload. Fails OPEN —
    any fault yields abstain (defer), never a silent block; non-negotiable
    denies are double-locked in the fail-closed native settings (ADR-002).

    Subject resolution (per issue #57):
      - ``as_subject`` given → that subject (a caller that names the subject
        it decides as — the CLI's probe)
      - ``agent_type`` present in payload → ``agent:<agent_type>`` (unchanged)
      - ``agent_type`` absent + ``project_root`` set + ``.claude/settings.json``
        has ``agent: X`` → ``agent:X`` (main session runs as the configured agent)
      - ``agent_type`` absent + no configured default → ``operator``

    Pass ``project_root`` (the adopter tree root) from the hook entry-point so
    main-session calls resolve to the configured agent, and so a file tool's
    target can be placed in the agent workspace (a path-scoped privilege);
    without a root no path-scoped privilege is recognized. The CLI's probe
    passes the root too, with ``as_subject`` naming the subject it probes.
    """
    try:
        return decide(model, catalog, _hook_request(payload, project_root, as_subject))
    except Exception as exc:  # fail-open
        return "abstain", f"hook fault → fail-open: {exc!r}"


def _hook_request(
    payload: dict[str, Any], project_root: str | None, as_subject: str | None
) -> dict[str, Any]:
    """The request `decide()` reads for a PreToolUse payload, with its subject
    resolved as `hook_decide` describes. Raises on a malformed payload."""
    agent_type = payload.get("agent_type")
    if as_subject:
        subject = as_subject
    elif agent_type:
        subject = f"agent:{agent_type}"
    elif project_root:
        default_agent = _read_default_agent(project_root)
        subject = f"agent:{default_agent}" if default_agent else "operator"
    else:
        subject = "operator"
    tool = payload["tool_name"]
    if tool == "Bash":
        return {
            "type": "bash",
            "command": payload["tool_input"]["command"],
            "cwd": payload.get("cwd", ""),
            "subject": subject,
        }
    return {
        "type": "tool",
        "tool": tool,
        "cwd": payload.get("cwd", ""),
        "subject": subject,
        # Surface the URL for domain-scoped privilege checks (web-fetch).
        # WebFetch and WebSearch both supply `url` in tool_input; absent
        # for all other tools.  A missing key becomes None, which _scope_ok
        # treats as an unparseable host → deny for domain-scoped grants.
        "url": payload.get("tool_input", {}).get("url"),
        # A file tool's target and the project root, for the path-scoped
        # privileges (the agent workspace).
        "path": _target_path(payload.get("tool_input", {})),
        "root": project_root,
    }


# ---- the guardrails a deferred command may hide (#1982) ---------------------
#
# Where the core abstains on a Bash command, a harness may still allow it by
# rules of its own, as Claude Code's baseline `Bash(git:*)` allows a deferred
# `git push origin --forc[e]`. ADR-025 point 2 makes that abstain a prompt, so
# the core names the guardrails that may bind on the command in a form it
# cannot see, and an adapter may ask the person rather than defer, as the
# Claude Code hook does. Only a guardrail's deny is named: it is the
# non-negotiable one (ADR-002 point 3), while a project's own deny rides the
# hook's speed bump.
# Nothing here changes a verdict of `decide()`.


def hidden_guardrails(
    model: dict[str, Any], catalog: dict[str, Any], request: dict[str, Any]
) -> dict[str, list[str]]:
    """The guardrails among the subject's denies that may bind on a Bash
    request in a form the core cannot see, and on none it can see, each with
    what keeps the core from seeing it, such as "a pathname pattern" (ADR-025
    points 2 and 5). A guardrail is a privilege the catalog flags
    `guardrail: true`. Each keeps `decide()` from allowing the request, whatever
    it abstained on first. Empty for a tool request."""
    if request.get("type") != "bash":
        return {}
    _, unseen = _deny_forms(catalog, request)
    privileges = catalog.get("privileges", {})
    denied: set[str] = set()
    for grant in _effective_grants(model, request["subject"]):
        if grant.get("effect", "allow") == "deny":
            denied |= _privilege_ids(grant.get("privilege"))
    return {
        name: sorted(_UNSEEN_KIND[kind] for kind in kinds)
        for name, kinds in sorted(unseen.items())
        if name in denied and privileges.get(name, {}).get("guardrail") is True
    }


def hook_hidden_guardrails(
    model: dict[str, Any],
    catalog: dict[str, Any],
    payload: dict[str, Any],
    project_root: str | None = None,
    *,
    as_subject: str | None = None,
) -> dict[str, list[str]]:
    """`hidden_guardrails` for a PreToolUse payload, its subject resolved as
    `hook_decide` resolves it. Fails open: a fault names no guardrail, so the
    caller keeps the abstain."""
    try:
        return hidden_guardrails(model, catalog, _hook_request(payload, project_root, as_subject))
    except Exception:
        return {}


def targets_path_scoped(
    catalog: dict[str, Any], payload: dict[str, Any], project_root: str | None
) -> bool:
    """Does a path-scoped privilege — the agent workspace — recognize this
    PreToolUse payload? File tools only, like the recognizer itself.

    The diagnostic loop's defect test (#1043): every shipped profile grants the
    workspace to every agent, so a prompt for a request it recognizes is a
    defect, not an allowlist gap. Never raises; any fault reads as False."""
    try:
        request = {
            "type": "tool",
            "tool": payload.get("tool_name"),
            "cwd": payload.get("cwd", ""),
            "path": _target_path(payload.get("tool_input") or {}),
            "root": project_root,
        }
        return bool(_path_scoped_privileges(catalog.get("privileges", {}), request))
    except Exception:
        return False


# ---- thin loaders ----------------------------------------------------------

# ---- stdlib YAML-subset fallback -------------------------------------------
# Used by load_yaml() when ruamel.yaml is not importable (e.g. inside macOS
# Seatbelt where uv cannot run — ADR-014). Handles the subset the shipped files
# use: block mappings, block sequences, single-quoted and double-quoted scalars,
# flow sequences ([a, b, c]), block scalars (>-), booleans, integers, null,
# and # comments. No anchors, aliases, merge-keys, flow mappings, multi-doc,
# or custom tags — none appear in the shipped files.
#
# Invariant (ADR-002/ADR-003 same-code): the fallback parses the shipped files
# IDENTICALLY to ruamel.yaml safe-load. Covered by the conformance fixture
# tests/test_permission_decide.py::test_stdlib_fallback_parses_identically_to_ruamel.


def _stdlib_load_yaml(text: str) -> Any:
    """Minimal YAML-subset parser (stdlib-only, no third-party deps)."""

    # ---- tokeniser helpers -------------------------------------------------

    def _parse_scalar(raw: str) -> Any:
        """Decode a YAML scalar string (already stripped) to a Python value."""
        s = raw.strip()
        if not s or s in ("~", "null", "Null", "NULL"):
            return None
        if s in ("true", "True", "TRUE"):
            return True
        if s in ("false", "False", "FALSE"):
            return False
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    def _unquote_single(s: str) -> str:
        """Strip surrounding single-quotes; handle '' → ' escape."""
        assert s.startswith("'") and s.endswith("'")
        return s[1:-1].replace("''", "'")

    def _unquote_double(s: str) -> str:
        """Strip surrounding double-quotes; handle \\n, \\t, \\\\ escapes."""
        assert s.startswith('"') and s.endswith('"')
        inner = s[1:-1]
        return (
            inner.replace('\\"', '"')
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\\\", "\\")
        )

    def _parse_value_token(token: str) -> Any:
        """Parse a single value token (scalar or simple unquoted string)."""
        t = token.strip()
        if t.startswith("'") and t.endswith("'") and len(t) >= 2:
            return _unquote_single(t)
        if t.startswith('"') and t.endswith('"') and len(t) >= 2:
            return _unquote_double(t)
        return _parse_scalar(t)

    def _split_flow_sequence(body: str) -> list:
        """Parse the interior of a flow sequence [...] into a Python list.
        Handles single- and double-quoted strings as atomic tokens."""
        items: list = []
        current = ""
        in_single = False
        in_double = False
        for ch in body:
            if ch == "'" and not in_double:
                in_single = not in_single
                current += ch
            elif ch == '"' and not in_single:
                in_double = not in_double
                current += ch
            elif ch == "," and not in_single and not in_double:
                s = current.strip()
                if s:
                    items.append(_parse_value_token(s))
                current = ""
            else:
                current += ch
        s = current.strip()
        if s:
            items.append(_parse_value_token(s))
        return items

    # ---- block-scalar collector (>- folded-strip, | literal-strip) ---------

    def _collect_block_scalar(lines: list, start_idx: int, indent: int) -> tuple[str, int]:
        """Collect lines for a block scalar starting at start_idx.
        Returns (scalar_value, next_line_index)."""
        # Determine the content indentation from the first non-empty content line.
        content_indent: int | None = None
        parts: list[str] = []
        i = start_idx
        while i < len(lines):
            raw = lines[i]
            stripped = raw.rstrip()
            if not stripped:
                parts.append("")
                i += 1
                continue
            col = len(stripped) - len(stripped.lstrip())
            if content_indent is None:
                content_indent = col
            if col < (content_indent if content_indent is not None else indent + 1):
                break
            parts.append(stripped[content_indent:] if content_indent else stripped)
            i += 1
        # Folded (>-): join non-empty runs with space, remove trailing newlines.
        result = " ".join(p for p in parts if p).rstrip()
        return result, i

    # ---- line preprocessor -------------------------------------------------

    def _strip_comment(line: str) -> str:
        """Remove inline # comments that are outside quotes."""
        out = ""
        in_single = False
        in_double = False
        for ch in line:
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                break
            out += ch
        return out.rstrip()

    # ---- recursive block parser --------------------------------------------

    def _parse_block(lines: list, idx: int, base_indent: int) -> tuple[Any, int]:
        """Parse a block node (mapping or sequence) at the given base_indent.
        Returns (value, next_idx)."""
        if idx >= len(lines):
            return None, idx

        result_map: dict | None = None
        result_seq: list | None = None
        i = idx

        while i < len(lines):
            raw = lines[i]
            stripped_raw = raw.rstrip()
            if not stripped_raw or stripped_raw.lstrip().startswith("#"):
                i += 1
                continue

            line = _strip_comment(stripped_raw)
            if not line.strip():
                i += 1
                continue

            col = len(line) - len(line.lstrip())

            # Back up to parent block
            if col < base_indent:
                break

            # New sibling at a HIGHER-than-expected indent inside parent — skip
            # (shouldn't happen in valid YAML, but be defensive).
            if col > base_indent and result_map is None and result_seq is None:
                # We're establishing the indent from the first entry.
                base_indent = col

            content = line.lstrip()

            # ---- sequence entry: starts with "- " --------------------------
            if content.startswith("- "):
                if result_map is not None:
                    break  # type switch — back to parent
                if result_seq is None:
                    result_seq = []
                value_part = content[2:].strip()
                if value_part:
                    # Inline value after "- "
                    if value_part.startswith("{"):
                        # Inline flow mapping — not needed for shipped files; skip.
                        result_seq.append(_parse_value_token(value_part))
                        i += 1
                    elif value_part.startswith("["):
                        body = value_part[1 : value_part.rfind("]")]
                        result_seq.append(_split_flow_sequence(body))
                        i += 1
                    elif value_part.startswith("'") or value_part.startswith('"'):
                        result_seq.append(_parse_value_token(value_part))
                        i += 1
                    elif ":" in value_part:
                        # Inline mapping key: value on same line as "- "
                        child_lines = []
                        # first key:value is on this line
                        child_indent = col + 2
                        child_lines.append(" " * child_indent + value_part)
                        j = i + 1
                        while j < len(lines):
                            r2 = lines[j].rstrip()
                            if not r2 or r2.lstrip().startswith("#"):
                                j += 1
                                continue
                            c2 = len(r2) - len(r2.lstrip())
                            if c2 <= col:
                                break
                            child_lines.append(r2)
                            j += 1
                        child_val, _ = _parse_block(child_lines, 0, child_indent)
                        result_seq.append(child_val)
                        i = j
                    else:
                        result_seq.append(_parse_scalar(value_part))
                        i += 1
                else:
                    # "- " alone — nested block
                    child_indent = col + 2
                    child_val, i = _parse_block(lines, i + 1, child_indent)
                    result_seq.append(child_val)
                continue

            # ---- bare "- " (dash alone on line) ----------------------------
            if content.strip() == "-":
                if result_seq is None:
                    result_seq = []
                result_seq.append(None)
                i += 1
                continue

            # ---- mapping key: value ----------------------------------------
            colon_pos = -1
            in_s = False
            in_d = False
            for ci, ch in enumerate(content):
                if ch == "'" and not in_d:
                    in_s = not in_s
                elif ch == '"' and not in_s:
                    in_d = not in_d
                elif ch == ":" and not in_s and not in_d:
                    colon_pos = ci
                    break

            if colon_pos == -1:
                # Plain scalar continuation — treat as bare value
                i += 1
                continue

            key_raw = content[:colon_pos].strip()
            key = _parse_value_token(key_raw) if key_raw else None
            val_raw = content[colon_pos + 1 :].strip()

            if result_seq is not None:
                break  # type switch
            if result_map is None:
                result_map = {}

            if not val_raw:
                # Value on subsequent lines
                i += 1
                # Peek at next non-blank, non-comment line
                j = i
                while j < len(lines):
                    r2 = lines[j].rstrip()
                    if not r2 or r2.lstrip().startswith("#"):
                        j += 1
                        continue
                    break
                if j >= len(lines):
                    result_map[key] = None
                    i = j
                    continue
                r2 = lines[j]
                c2 = len(r2) - len(r2.lstrip())
                # A block sequence is a valid mapping value at the SAME indent
                # level as the key — the "- " indicator provides the structural
                # indent for the sequence entries' content.  Without this check
                # the grants.yaml shape (key at col 0, "- " entries at col 0)
                # parses to None, silently dropping all adopter grants and
                # causing the zero-dep hook to fail open (issue #55).
                _r2_content = r2.lstrip()
                _same_level_seq = c2 == col and (_r2_content.startswith("- ") or _r2_content == "-")
                if c2 > col or _same_level_seq:
                    # Child block (deeper indent, OR same-indent block sequence)
                    child_val, i = _parse_block(lines, j, c2)
                    result_map[key] = child_val
                else:
                    result_map[key] = None
                continue
            else:
                # Inline value
                v = val_raw
                if v.startswith(">-") or v.startswith("|"):
                    # Block scalar
                    scalar_val, i = _collect_block_scalar(lines, i + 1, col + 1)
                    result_map[key] = scalar_val
                elif v.startswith("["):
                    close = v.rfind("]")
                    if close != -1:
                        body = v[1:close]
                        result_map[key] = _split_flow_sequence(body)
                    else:
                        result_map[key] = v
                    i += 1
                elif v.startswith("'") or v.startswith('"'):
                    result_map[key] = _parse_value_token(v)
                    i += 1
                else:
                    result_map[key] = _parse_scalar(v)
                    i += 1
                continue

        if result_map is not None:
            return result_map, i
        if result_seq is not None:
            return result_seq, i
        return None, i

    # ---- entry point -------------------------------------------------------
    lines = text.splitlines()
    # Strip document-start marker
    clean: list[str] = []
    for ln in lines:
        s = ln.rstrip()
        if s.lstrip() in ("---", "..."):
            continue
        clean.append(ln)
    result, _ = _parse_block(clean, 0, 0)
    return result if result is not None else {}


def load_yaml(path: str) -> dict[str, Any]:
    """Load a YAML file, returning a dict. Uses ruamel.yaml when available
    (the kit-wide library); falls back to the stdlib-only subset parser
    when ruamel.yaml is not importable (e.g. inside macOS Seatbelt, ADR-014).

    The stdlib fallback is in this SHARED loader — not duplicated in the hook
    — so the hook and the `pkit permissions` CLI reach identical parse results
    through the same code path (ADR-002/ADR-003 same-code invariant).
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        from ruamel.yaml import YAML as _YAML

        _yaml = _YAML(typ="safe")
        import io as _io

        result = _yaml.load(_io.StringIO(text))
    except ImportError:
        result = _stdlib_load_yaml(text)
    # Coerce a non-dict document (bare scalar, top-level list, empty/None) to {}
    # on BOTH parse paths. A hand-corrupted sidecar that parses to a scalar or
    # list must not make a downstream `.get()` raise under one parser (ruamel,
    # CLI) while degrading to {} under the other (stdlib, sandboxed hook) — the
    # same-code invariant (ADR-002/ADR-003) requires identical results.
    return result if isinstance(result, dict) else {}


def _exists(path: str) -> bool:
    import os.path

    return os.path.isfile(path)


def _capability_fragment_catalog(
    target_root: str, backbone_ids: set[str]
) -> tuple[dict[str, Any], list[str]]:
    """Privilege definitions contributed by installed capabilities (ADR-021).

    Walks the manifest ``components:`` list (the same install-state-as-gate the
    grants walk uses — NOT a glob of ``.pkit/capabilities/``) and for each
    component of kind ``capability`` reads its catalog fragment at
    ``.pkit/capabilities/<name>/permissions/privilege-catalog.yaml`` if present.
    An uninstalled or orphan capability directory contributes nothing.

    Returns ``(merged_privileges, rejections)``: a map of accepted scoped
    privilege ids → spec (each stamped ``provenance: capability:<name>`` for the
    reporting surface), and a list of human-readable rejection reasons.

    Three merge constraints (ADR-021), enforced here *before* the catalog
    reaches ``guardrail_denies`` or ``decide``:

    - **Capability-scoped ids.** A fragment id is rewritten to ``<cap>:<name>``
      regardless of how the fragment authored it, so attribution is intrinsic
      and a fragment can only ever introduce ids in its own namespace.
    - **Collision-rejecting.** A scoped id colliding with a backbone privilege
      or another capability's already-merged id is rejected (the colliding
      entry is dropped, not overwritten) — a fragment can never shadow or strip
      an existing definition.
    - **Guardrail-forbidding.** A fragment privilege carrying ``guardrail:
      true`` is rejected (dropped), so a capability can never install a deny
      that applies to every adopter by default.

    A rejected entry contributes NOTHING to the merged catalog rather than
    aborting the load: the backbone catalog stays intact, and the capability's
    own deny grant then references a privilege that does not exist (matching no
    request) — fail-CLOSED on the fragment's vocabulary, never a false allow.

    Stdlib-safe (ADR-002 / ADR-003 same-code invariant): reads through the
    existing ``load_yaml`` / ``_stdlib_load_yaml`` fallback and the existing
    manifest read; no third-party dependency, no ``src/project_kit`` import.
    """
    import os.path

    manifest_path = os.path.join(target_root, ".pkit", "manifest.yaml")
    if not _exists(manifest_path):
        return {}, []
    manifest = load_yaml(manifest_path)
    merged: dict[str, Any] = {}
    rejections: list[str] = []
    for component in manifest.get("components", []) or []:
        if not isinstance(component, dict):
            continue
        if component.get("kind") != "capability":
            continue
        name = component.get("name")
        if not name:
            continue
        frag_path = os.path.join(
            target_root,
            ".pkit",
            "capabilities",
            name,
            "permissions",
            "privilege-catalog.yaml",
        )
        if not _exists(frag_path):
            continue
        doc = load_yaml(frag_path)
        for raw_id, spec in (doc.get("privileges", {}) or {}).items():
            if not isinstance(spec, dict):
                continue
            scoped_id = f"{name}:{raw_id}"
            if spec.get("guardrail"):
                rejections.append(
                    f"{scoped_id}: a capability fragment may not define a guardrail (rejected)"
                )
                continue
            if scoped_id in backbone_ids or scoped_id in merged:
                rejections.append(f"{scoped_id}: id collides with an existing privilege (rejected)")
                continue
            entry = dict(spec)
            entry["provenance"] = f"capability:{name}"
            merged[scoped_id] = entry
    return merged, rejections


def load_catalog(target_root: str) -> dict[str, Any]:
    """Load the privilege catalog, merging installed capabilities' fragments.

    The merge lives HERE (not in ``load_model``) because both the PreToolUse
    hook and the ``pkit permissions`` CLI call ``load_catalog`` directly to
    learn which commands are recognised, and ``guardrail_denies`` runs on
    whatever this returns — so both readers get the identical merged catalog
    and the guardrail check gates the result before any deny is derived
    (ADR-021 decision 1; ADR-002 same-code invariant).

    The backbone catalog (``.pkit/schemas/privilege-catalog.yaml``) is the base;
    installed capabilities' fragments are merged in additively under the
    collision-rejecting, guardrail-forbidding rule of
    ``_capability_fragment_catalog``.
    """
    import os.path

    path = os.path.join(target_root, ".pkit", "schemas", "privilege-catalog.yaml")
    catalog = load_yaml(path) if _exists(path) else {}
    privileges = catalog.setdefault("privileges", {}) if isinstance(catalog, dict) else {}
    if not isinstance(privileges, dict):
        return catalog
    fragments, rejections = _capability_fragment_catalog(target_root, set(privileges))
    privileges.update(fragments)
    if rejections:
        # Surface rejected fragments on the catalog so the reporting layer can
        # show them; never silent (ADR-021 decision 6 — visibility).
        catalog["_fragment_rejections"] = rejections
    return catalog


def guardrail_denies(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Synthesize baseline `{subject: all, effect: deny}` grants for every
    privilege the catalog flags `guardrail: true`. The catalog is the single
    source of truth for the guardrail deny set (ADR-002's double-lock): these
    are the fail-open hook half; the harness ships matching fail-closed native
    denies. Returns one deny grant per guardrail privilege, sorted by id."""
    out: list[dict[str, Any]] = []
    for pid in sorted(catalog.get("privileges", {})):
        if catalog["privileges"][pid].get("guardrail"):
            out.append(
                {"subject": "all", "privilege": f"[privilege-catalog:{pid}]", "effect": "deny"}
            )
    return out


def active_profile(target_root: str, config: dict[str, Any]) -> Any:
    """Resolve the active permission profile name for a target tree (ADR-032).

    `active_profile` is per-machine state (an operator's autonomy choice), so it
    lives in a gitignored per-machine sidecar (`active-profile.yaml`, declared
    `runtime_ignore`), NOT in the tracked `config.yaml`. This is the SINGLE
    resolution point — the source of truth both the hook and the CLI read
    through (ADR-002/ADR-003 same-code invariant), so each operator's hook layers
    their own profile while the shared `config.yaml` policy stays committed.

    Resolution order: the sidecar's `active_profile` key, then a `config.yaml`
    fallback. The fallback is PERMANENT (issue #304): an adopter installed before
    ADR-032 — or mid-migration before the next `setup autonomy` relocation —
    still has `active_profile` in `config.yaml`, and reading it there keeps
    enforcement unchanged for them. The fallback is the simplest safe rule (read
    sidecar, else config) and costs nothing once the value is relocated, so it
    stays rather than being a removable migration crutch.

    Stdlib-safe (same-code invariant): reads through the shared `load_yaml` /
    `_stdlib_load_yaml` fallback; no third-party dependency, no
    `src/project_kit` import — decide.py runs as bare python in-sandbox."""
    import os.path

    sidecar = os.path.join(target_root, ".pkit", "permissions", "project", "active-profile.yaml")
    if _exists(sidecar):
        name = load_yaml(sidecar).get("active_profile")
        if name:
            return name
    return config.get("active_profile")


def _active_profile_grants(target_root: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Grants contributed by the active permission profile (per ADR-005), if any.

    The profile is a LAYER, never an owner: its grants sit between the guardrail
    denies and the adopter's own grants.yaml, and the adopter's grants are
    unioned last so a manual `grant`/`revoke` is never overwritten by a profile.
    Resolves the active profile name via `active_profile` (the per-machine
    sidecar, with `config.yaml` fallback — ADR-032), then the profile file
    project-first (`project/profiles/<name>.yaml`) then shipped
    (`profiles/<name>.yaml`).

    Each grant dict is annotated with a ``_profile`` key naming the source
    profile (mirroring ``_capability_fragment_grants``' ``_capability``
    annotation). This is ADR-046's routing key: `apply` uses it to route
    profile-only realizer output to the per-machine settings file. The
    annotation rides along in the model unstripped — ``decide()`` reads only
    ``subject``/``privilege``/``effect``/``scope`` and ignores extra keys."""
    import os.path

    name = active_profile(target_root, config)
    if not name:
        return []
    for base in (
        os.path.join(target_root, ".pkit", "permissions", "project", "profiles"),
        os.path.join(target_root, ".pkit", "permissions", "profiles"),
    ):
        path = os.path.join(base, f"{name}.yaml")
        if _exists(path):
            out: list[dict[str, Any]] = []
            for grant in load_yaml(path).get("grants", []) or []:
                if isinstance(grant, dict):
                    annotated = dict(grant)
                    annotated["_profile"] = name
                    out.append(annotated)
                else:
                    out.append(grant)
            return out
    return []


def _capability_fragment_grants(target_root: str) -> list[dict[str, Any]]:
    """Grants contributed by installed capabilities (ADR-016).

    Walks the manifest ``components:`` list (NOT a glob of ``.pkit/capabilities/``)
    and for each component of kind ``capability`` reads its grants fragment at
    ``.pkit/capabilities/<name>/permissions/grants.yaml`` if present. An
    uninstalled or orphan capability directory contributes nothing — only
    manifest-registered components count.

    Each grant dict is annotated with a ``_capability`` key naming the source
    capability; ``load_model`` carries this through for the reporting layer
    (``pkit permissions overview`` / ``explain``). The annotation is never
    stripped — it rides along in the model, and ``decide()`` simply ignores
    keys it does not read (it reads only ``subject``, ``privilege``,
    ``effect``, and ``scope``). The profile layer's ``_profile`` annotation
    (ADR-046 routing key) works the same way.

    Stdlib-safe (ADR-002 / ADR-003 same-code invariant): reads files through
    the existing ``load_yaml`` / ``_stdlib_load_yaml`` fallback; no third-party
    dependency, no ``src/project_kit`` import.
    """
    import os.path

    manifest_path = os.path.join(target_root, ".pkit", "manifest.yaml")
    if not _exists(manifest_path):
        return []
    manifest = load_yaml(manifest_path)
    out: list[dict[str, Any]] = []
    for component in manifest.get("components", []) or []:
        if not isinstance(component, dict):
            continue
        if component.get("kind") != "capability":
            continue
        name = component.get("name")
        if not name:
            continue
        frag_path = os.path.join(
            target_root, ".pkit", "capabilities", name, "permissions", "grants.yaml"
        )
        if not _exists(frag_path):
            continue
        doc = load_yaml(frag_path)
        for grant in doc.get("grants", []) or []:
            if isinstance(grant, dict):
                annotated = dict(grant)
                annotated["_capability"] = name
                out.append(annotated)
    return out


def load_model(target_root: str, catalog: dict[str, Any]) -> dict[str, Any]:
    """Build the effective permission model for a target tree: the catalog-
    derived guardrail denies, then installed-capability fragments, then the
    active profile's grant-layer, then the adopter's authored grants — unioned
    in that order — plus posture/ownership_mode from project config.

    This is the SINGLE model loader (ADR-002's same-code invariant): the
    PreToolUse hook and the `pkit permissions` CLI both call it, so they decide
    and display from byte-identical models. Order is guardrails → capability
    fragments → profile → adopter (adopter last so manual grants are never
    clobbered, per ADR-005); `decide()` is deny-wins and order-independent
    regardless. Capability-fragment grants are annotated with ``_capability``
    for the reporting layer (ADR-016) and profile-layer grants with ``_profile``
    (ADR-046's realizer routing key); ``decide()`` ignores the extra keys.
    """
    import os.path

    perm_dir = os.path.join(target_root, ".pkit", "permissions", "project")
    grants_path = os.path.join(perm_dir, "grants.yaml")
    config_path = os.path.join(perm_dir, "config.yaml")
    grants_doc = load_yaml(grants_path) if _exists(grants_path) else {}
    config = load_yaml(config_path) if _exists(config_path) else {}
    return {
        "posture": config.get("posture", "lenient"),
        "ownership_mode": config.get("ownership_mode", "additive"),
        # `active_profile` is a decision-model input (it layers the profile's
        # grants below), and per ADR-032 it lives in the per-machine sidecar with
        # a `config.yaml` fallback — resolved through the single `active_profile`
        # helper so the hook and the CLI read the same per-machine source. This is
        # an ADDITIVE source-edit: `decide()`'s verdict path is byte-identical.
        "active_profile": active_profile(target_root, config),
        "grants": (
            guardrail_denies(catalog)
            + _capability_fragment_grants(target_root)
            + _active_profile_grants(target_root, config)
            + list(grants_doc.get("grants", []) or [])
        ),
    }
