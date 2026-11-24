#!/usr/bin/env bash
# project-management 0.58.0 — resource: warn of what an app's credential changes.
#
# [project-management:DEC-076-app-credentials] has no person stand for the
# acting account under a credential that names no user's account. Two things a
# project holds may then mean something they no longer do, and this migration
# warns of each. It writes nothing: which account an entry means, and what a
# workflow should name, are the project's to decide.
#
#   1. A bare entry of `project/members.yaml` whose name, with the `[bot]`
#      suffix, GitHub answers as an account of type `Bot`. The closed gate now
#      matches a bot's account only by its own login, `<name>[bot]`, and a bare
#      entry no longer passes an App's credential (point 2). The lookup of the
#      bare login chooses the message: where no account bears it, the entry
#      can only mean the App's; where a user's account bears it, it may mean
#      either.
#   2. A workflow under `.github/workflows/` that sets `PM_INVOKER_LOGIN`. The
#      variable no longer names the acting account: it names only the person
#      the agent works for, who serves as the default assignee and for
#      start-work and next-task, and passes no gate (point 3).
#
# A lookup that gives no answer (offline, `gh` missing, a refusal, a rate limit)
# is said, and the entry is named for the person to check. Idempotent: it
# writes nothing, so a second run says the same, and where it finds nothing to
# warn of it says so and exits clean.
#
# Run via the upgrade runtime with ROOT=<adopter root>.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${ROOT:?ROOT must be set by the upgrade runtime}"

CAP_DIR="$ROOT/.pkit/capabilities/project-management"
MEMBERS="$CAP_DIR/project/members.yaml"
WORKFLOWS="$ROOT/.github/workflows"

if [ ! -d "$CAP_DIR" ]; then
    echo "  [skip] project-management capability not installed at $CAP_DIR"
    exit 0
fi

warned=0

# Each `github_login:` value of the member list, read line by line: the runtime
# guarantees only bash and stdlib python3, so no YAML parser is used.
member_logins() {
    python3 - "$MEMBERS" <<'PYEOF'
import re
import sys

LOGIN = re.compile(r"^\s*-?\s*github_login\s*:\s*([^#\s]+)")
for line in open(sys.argv[1], encoding="utf-8"):
    match = LOGIN.match(line)
    if match:
        print(match.group(1).strip("'\""))
PYEOF
}

# The host the capability's requests go to, where its configuration pins one
# (DEC-023); `gh`'s own otherwise.
CONFIG="$CAP_DIR/project/config.yaml"
host=""
if [ -f "$CONFIG" ] && command -v python3 >/dev/null 2>&1; then
    host=$(python3 - "$CONFIG" <<'PYEOF'
import re
import sys

inside = False
for line in open(sys.argv[1], encoding="utf-8"):
    if re.match(r"^gh\s*:", line):
        inside = True
        continue
    if inside and re.match(r"^\S", line):
        break
    found = re.match(r"^\s+host\s*:\s*['\"]?([^'\"#\s]+)", line) if inside else None
    if found:
        print(found.group(1))
        break
PYEOF
)
fi
if [ -n "$host" ]; then
    export GH_HOST="$host"
fi

#: What respelling an entry admits (DEC-076 point 2).
ADMITS="An entry in that spelling admits every session that holds a credential whose account it names, every run under the App's token among them."

# 1. Bare member entries an App's account bears the name of.
if [ -f "$MEMBERS" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "  [warn] python3 is not on PATH, so the member entries of $MEMBERS were not read" >&2
        warned=1
    else
        logins=$(member_logins)
        for login in $logins; do
            case "$login" in
                *\[bot\]|*\[BOT\]|app/*) continue ;;
            esac
            if ! command -v gh >/dev/null 2>&1; then
                echo "  [warn] members.yaml: \`gh\` is not on PATH, so whether the entry $login names an App's account could not be asked. An App's account passes the closed gate only as ${login}[bot] (DEC-076 point 2)." >&2
                warned=1
                continue
            fi
            # Only GitHub's definite answer that the suffixed login is a bot's
            # is a sign; no answer at all is none.
            bot_type=$(gh api "users/${login}[bot]" --jq .type 2>/dev/null) || bot_type=""
            if [ "$bot_type" != "Bot" ]; then
                continue
            fi
            bare_said=""
            if bare_type=$(gh api "users/${login}" --jq .type 2>&1); then
                bare_said="names the $bare_type account $login"
            elif [ -z "$host" ] && printf '%s' "$bare_type" | grep -q "HTTP 404"; then
                bare_said=""
            else
                bare_said="could not be told apart: GitHub gave no definite answer for the login $login"
            fi
            if [ -z "$bare_said" ]; then
                echo "  [warn] members.yaml: the entry $login names an App's account, ${login}[bot], since GitHub knows no account by the bare login. The closed gate matches an App's account only by its own login, so the entry passes it only as ${login}[bot] (DEC-076 point 2). $ADMITS" >&2
            else
                echo "  [warn] members.yaml: the entry $login may mean either of two accounts: it $bare_said, and GitHub answers ${login}[bot] as an App's account. Where it means the App, write it ${login}[bot], since the closed gate matches an App's account only by its own login; where it means the other, leave it (DEC-076 point 2). $ADMITS" >&2
            fi
            warned=1
        done
    fi
fi

# 2. Workflows that set PM_INVOKER_LOGIN.
if [ -d "$WORKFLOWS" ]; then
    for workflow in "$WORKFLOWS"/*.yml "$WORKFLOWS"/*.yaml; do
        [ -f "$workflow" ] || continue
        if grep -q "PM_INVOKER_LOGIN" "$workflow"; then
            echo "  [warn] ${workflow#"$ROOT"/} sets PM_INVOKER_LOGIN. Under a credential that names no user's account, such as the workflow's own token or an App's, the variable no longer passes the membership gate: the run passes only where the backbone's reading names its account and an entry names that account. The variable now names only the person the agent works for, the default assignee and the person start-work and next-task work for (DEC-076 points 2 and 3)." >&2
            warned=1
        fi
    done
fi

if [ "$warned" -eq 0 ]; then
    echo "  [ok] no member entry or workflow that an app's credential changes the meaning of. Not read: a setup outside the repository, and the value of a secret, so a bare entry such a setup matched is found only at the gate's refusal, which names it."
fi
exit 0
