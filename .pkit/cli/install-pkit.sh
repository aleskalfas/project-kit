#!/bin/sh
#
# install-pkit.sh: install this project's pkit on a machine with nobody at the
# keyboard, such as a pipeline's runner, a container or a hosted agent's
# machine (ADR-090). Run it as
#
#     sh .pkit/cli/install-pkit.sh
#
# It installs the version the project pins (`.pkit/version-pin`), or else the
# backbone version its manifest records, and never `latest`, through
# `uv tool install` from the distribution URL at that release's tag. It
# installs only where it finds no pkit installed, so it never replaces a tool
# other projects on the machine may run. Then it runs the `pkit` the PATH
# finds, from the project's root, and succeeds only where that reports the
# project's version.
#
# It acts on the project it sits in, found from its own place in the tree, not
# from the working directory. It runs only when invoked: no hook and no pkit
# command runs it. It takes no arguments. The CLI reference,
# `.pkit/cli/README.md`, "Installing pkit on PATH", documents it.

set -u

# The distribution URL in uv's spelling: the URL compiled into the tool,
# `router.DISTRIBUTION_GIT_URL`. The script keeps its own copy, since it runs
# before any pkit exists to ask, and a test holds the two equal (ADR-090
# point 7). A fork puts its own URL in both.
DISTRIBUTION_GIT_URL="git+https://github.com/aleskalfas/project-kit.git"

# The characters a read of the pin strips from both ends, as the router's
# `str.strip()` does: space, tab, carriage return, vertical tab, form feed and
# newline.
BLANKS=$(printf ' \t\r\v\f.')
BLANKS="${BLANKS%.}
"

say() {
    printf 'install-pkit: %s\n' "$1"
}

# Print each argument as a line of an error on standard error, and exit 1.
fail() {
    printf 'install-pkit: error: %s\n' "$1" >&2
    shift
    for line in "$@"; do
        printf '  %s\n' "$line" >&2
    done
    exit 1
}

# Print $1 with the blanks around it stripped.
strip() {
    stripped=$1
    while :; do
        case $stripped in
            [$BLANKS]*) stripped=${stripped#?} ;;
            *) break ;;
        esac
    done
    while :; do
        case $stripped in
            *[$BLANKS]) stripped=${stripped%?} ;;
            *) break ;;
        esac
    done
    printf '%s' "$stripped"
}

# True where $1 is a release version, MAJOR.MINOR.PATCH, no part padded by a
# leading zero: the only pin the router can route, and the only version a
# release tag names.
is_release_version() {
    case $1 in
        *[!0123456789.]*) return 1 ;;
    esac
    major=${1%%.*}
    rest=${1#*.}
    [ "$rest" != "$1" ] || return 1
    minor=${rest%%.*}
    patch=${rest#*.}
    [ "$patch" != "$rest" ] || return 1
    case $patch in
        *.*) return 1 ;;
    esac
    for part in "$major" "$minor" "$patch"; do
        case $part in
            '' | 0?*) return 1 ;;
        esac
    done
    return 0
}

# Print the path of the file $1, with each symbolic link on the way followed
# and its folder read as the file system holds it.
physical_path() {
    target=$1
    hops=0
    while [ -L "$target" ] && [ "$hops" -lt 40 ]; do
        link=$(readlink -- "$target") || break
        case $link in
            /*) target=$link ;;
            *) target=${target%/*}/$link ;;
        esac
        hops=$((hops + 1))
    done
    folder=$(cd -- "${target%/*}" 2>/dev/null && pwd -P) || {
        printf '%s' "$target"
        return
    }
    printf '%s/%s' "$folder" "${target##*/}"
}

# The folder uv puts a tool's command in, or a way to ask for it.
uv_command_folder() {
    uv tool dir --bin 2>/dev/null || printf '%s' "the folder \`uv tool dir --bin\` prints"
}

if [ "$#" -gt 0 ]; then
    printf 'install-pkit: error: takes no arguments. Run it as: sh %s\n' "$0" >&2
    exit 2
fi

# --- The project it sits in ----------------------------------------------

case $0 in
    */*) script_folder=${0%/*} ;;
    *) script_folder=. ;;
esac
script_folder=$(cd -- "$script_folder" && pwd -P) || exit 1
pkit_folder=${script_folder%/*}
project_root=${pkit_folder%/*}
dispatcher=$script_folder/pkit

# --- The version to install: the pin, or else the recorded version -------

pin=
pin_file=$pkit_folder/version-pin
if [ -f "$pin_file" ] && pin_text=$(cat -- "$pin_file" 2>/dev/null); then
    pin=$(strip "$pin_text")
fi

if [ -n "$pin" ]; then
    if ! is_release_version "$pin"; then
        fail "this project's pin, '$pin' in $pin_file, is no release version MAJOR.MINOR.PATCH, so the router cannot run it. Nothing was installed." \
            "Mend the pin: \`pkit pin <version>\` writes a release version, or remove the file to install the version the project records."
    fi
    version=$pin
    source_of_version="the version this project pins"
else
    manifest=$pkit_folder/manifest.yaml
    recorded=
    if [ -f "$manifest" ]; then
        recorded=$(tr -d '\r' <"$manifest" | sed -n 's/^backbone_version:[ 	]*\([^ 	#]*\).*$/\1/p' | sed -n '1p')
        case $recorded in
            \"*\")
                recorded=${recorded#\"}
                recorded=${recorded%\"}
                ;;
            \'*\')
                recorded=${recorded#\'}
                recorded=${recorded%\'}
                ;;
        esac
    fi
    if [ -z "$recorded" ]; then
        fail "this project pins no version, and $manifest records no backbone_version, so there is no version to install. Nothing was installed." \
            "Choose a version and install it as the CLI reference's section \"Installing pkit on PATH\" says ($script_folder/README.md)."
    fi
    if ! is_release_version "$recorded"; then
        fail "this project pins no version, and the backbone_version $manifest records, '$recorded', is no release version. Nothing was installed." \
            "Choose a version and install it as the CLI reference's section \"Installing pkit on PATH\" says ($script_folder/README.md)."
    fi
    version=$recorded
    source_of_version="the version this project records"
fi

# --- What the machine holds ----------------------------------------------

if ! command -v uv >/dev/null 2>&1; then
    fail "\`uv\` is not on the PATH, and pkit needs it. Nothing was installed." \
        "Install uv (https://docs.astral.sh/uv/), put the folder it is in on the PATH, and run this script again."
fi

if ! tools=$(uv tool list 2>/dev/null); then
    fail "\`uv tool list\` failed, so this script cannot tell whether a pkit is installed. Nothing was installed."
fi
installed=
case "
$tools
" in
    *"
project-kit "* | *"
- pkit
"*) installed="uv lists it among its tools" ;;
esac

if [ -z "$installed" ]; then
    set -f
    saved_ifs=$IFS
    IFS=:
    for folder in ${PATH-}; do
        [ -n "$folder" ] || folder=.
        candidate=$folder/pkit
        if [ -f "$candidate" ] && [ -x "$candidate" ] &&
            [ "$(physical_path "$candidate")" != "$(physical_path "$dispatcher")" ]; then
            installed="the PATH finds $candidate"
            break
        fi
    done
    IFS=$saved_ifs
    set +f
fi

# --- The install, only where no pkit is installed ------------------------

if [ -n "$installed" ]; then
    say "a pkit is installed already ($installed), so this script installs nothing and leaves it as it is."
else
    say "installing pkit $version, $source_of_version: uv tool install $DISTRIBUTION_GIT_URL@v$version"
    if ! GIT_TERMINAL_PROMPT=0 uv tool install "$DISTRIBUTION_GIT_URL@v$version"; then
        fail "the install of pkit $version failed, as uv says above." \
            "Where a sandbox keeps writes out of uv's folders, run this script where it may write there."
    fi
fi

# --- The check: the pkit this project's commands run ---------------------

path_pkit=$(command -v pkit 2>/dev/null) || path_pkit=
if [ -z "$path_pkit" ]; then
    fail "the PATH finds no \`pkit\`." \
        "uv put the command in $(uv_command_folder): add that folder to the PATH, and run this script again."
fi
case $path_pkit in
    /*) ;;
    *) path_pkit=$PWD/$path_pkit ;;
esac

is_source_repository=
if [ -f "$project_root/src/project_kit/__init__.py" ] && [ -d "$pkit_folder" ]; then
    is_source_repository=yes
fi
if [ -z "$is_source_repository" ] &&
    [ "$(physical_path "$path_pkit")" = "$(physical_path "$dispatcher")" ]; then
    fail "the PATH finds this project's own dispatcher, $path_pkit, before the installed pkit, and the dispatcher only names this script." \
        "Put uv's command folder, $(uv_command_folder), before it on the PATH, and run this script again."
fi

reported=$(cd -- "$project_root" && GIT_TERMINAL_PROMPT=0 "$path_pkit" --version)
checked=$?
ran=$(printf '%s\n' "$reported" | awk 'NF { last = $NF } END { print last }')

if [ "$checked" -eq 0 ] && [ "$ran" = "$version" ]; then
    say "this project's commands run pkit $version, $source_of_version ($path_pkit)."
    exit 0
fi

if [ "$checked" -ne 0 ] || [ -z "$ran" ]; then
    ran_said="reports no version"
else
    ran_said="runs pkit $ran"
fi
fail "the pkit this project's commands run, $path_pkit, $ran_said, not $version, $source_of_version. The installed pkit was left as it is." \
    "To run this project's version without moving it: uvx --from $DISTRIBUTION_GIT_URL@v$version project-kit <command>" \
    "To make $version the pkit this machine runs, whoever owns the machine runs, on purpose: uv tool install --force $DISTRIBUTION_GIT_URL@v$version"
