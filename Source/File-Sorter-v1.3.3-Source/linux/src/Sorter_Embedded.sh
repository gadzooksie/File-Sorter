#!/usr/bin/env bash
# File Sorter v1.1.2. Editable rules, folders and destinations.
# Rules are reloaded each scan; they contain data, never shell code.
shopt -s nullglob
SCAN_INTERVAL="${SCAN_INTERVAL:-2}"
ARCHIVE_OLD_AFTER=$((72 * 60 * 60))
if [[ "${XDG_CONFIG_HOME:-}" == /* ]]; then
    CONFIG_DIR="$XDG_CONFIG_HOME/sorter-config"
else
    CONFIG_DIR="$HOME/.config/sorter-config"
fi
SORTER_DIRS_FILE="${SORTER_DIRS_FILE:-$CONFIG_DIR/directories.txt}"
SORTER_RULES_FILE="${SORTER_RULES_FILE:-$CONFIG_DIR/rules.tsv}"
SORTER_OVERWRITE_FILE="${SORTER_OVERWRITE_FILE:-$CONFIG_DIR/overwrite-files.txt}"
OVERWRITE_FILES=0
SCRIPT_PATH="$(realpath -e -- "${BASH_SOURCE[0]}" 2>/dev/null || printf '%s' "${BASH_SOURCE[0]}")"
DEFAULT_RULES=$(cat <<'GC_DEFAULTS_EOF'
# File Sorter v3: scope, pattern, destination, mode (tab-separated)
watch	*.7z	~/Downloads/Archives	archive
watch	*.zip	~/Downloads/Archives	archive
watch	*.tar.gz	~/Downloads/Archives	archive
watch	*.tar	~/Downloads/Archives	archive
watch	*.rar	~/Downloads/Archives	archive
watch	*.txt	~/Sorted/Text Files/txt	move
watch	*.ini	~/Sorted/Text Files/ini	move
watch	*.cfg	~/Sorted/Configs	move
watch	*.config	~/Sorted/Configs	move
watch	*.dll	~/Sorted/DLLs	move
watch	*.pdf	~/Sorted/PDFs	move
watch	*.bin	~/Sorted/Binaries	move
watch	*.BIN	~/Sorted/Binaries	move
watch	*.dat	~/Sorted/Data Files	move
watch	*.sh	~/Sorted/Shell Scripts	move
watch	*.log	~/Sorted/Log Files	move
watch	*.json	~/Sorted/JSONs	move
watch	*.js	~/Sorted/Java Script Files	move
watch	*.md	~/Sorted/Markdown Files	move
watch	*.bak	~/Sorted/Backup Files	move
watch	*.backup	~/Sorted/Backup Files	move
watch	*.lua	~/Sorted/Lua Scripts	move
watch	*.ps1	~/Sorted/Power Shell Scripts	move
watch	*.csv	~/Sorted/CSVs	move
watch	*.cs	~/Sorted/C# Files	move
watch	*.CS	~/Sorted/C# Files	move
watch	*.py	~/Sorted/Python Scripts	move
home	*.log	~/Sorted/Log Files	move
home	*.md	~/Sorted/Markdown Files	move
home	*.cs	~/Sorted/C# Files	move
home	*.CS	~/Sorted/C# Files	move
home	*.pdf	~/Sorted/PDFs	move
home	*.js	~/Sorted/Java Scripts	move
home	*.py	~/Sorted/Python Scripts	move
home	*.txt	~/Sorted/Text Files/txt	move
watch	*.AppImage	~/Sorted/AppImages	move
GC_DEFAULTS_EOF
)

declare -a scopes patterns destinations modes
rule_count=0

expand_path() {
    local raw="$1"
    case "$raw" in
        '~') printf '%s' "$HOME" ;;
        '~/'*) printf '%s' "$HOME/${raw:2}" ;;
        /*) printf '%s' "$raw" ;;
        *) return 1 ;;
    esac
}

load_rules() {
    local scope pattern destination mode extra
    scopes=(); patterns=(); destinations=(); modes=(); rule_count=0
    if [[ ! -r "$SORTER_RULES_FILE" ]]; then
        printf 'Warning: no rules file: %s\n' "$SORTER_RULES_FILE" >&2
        return 1
    fi
    while IFS=$'\t' read -r scope pattern destination mode extra || [[ -n "$scope$pattern$destination$mode" ]]; do
        [[ "$scope" == \#* || -z "$scope" ]] && continue
        [[ "$scope" == watch || "$scope" == home || "$scope" == saves ]] || continue
        [[ "$mode" == move || "$mode" == archive ]] || continue
        [[ -n "$pattern" && -n "$destination" && -z "$extra" ]] || continue
        [[ "$pattern" != */* && "$pattern" != *$'\n'* ]] || continue
        [[ "$destination" != *$'\n'* && "$destination" != *$'\r'* ]] || continue
        if [[ "$mode" == archive && "$pattern" != \*.* ]]; then continue; fi
        local realdest
        realdest="$(expand_path "$destination")" || continue
        [[ "$realdest" != / && "$realdest" != "$HOME" ]] || continue
        scopes+=("$scope"); patterns+=("$pattern"); destinations+=("$realdest"); modes+=("$mode")
        ((rule_count+=1))
    done < "$SORTER_RULES_FILE"
}

load_overwrite() {
    # Missing, unreadable, and malformed values always mean OFF.
    OVERWRITE_FILES=0
    local setting=''
    if [[ -f "$SORTER_OVERWRITE_FILE" && ! -L "$SORTER_OVERWRITE_FILE" ]]; then
        IFS= read -r setting < "$SORTER_OVERWRITE_FILE" || true
        [[ "$setting" == on ]] && OVERWRITE_FILES=1
    fi
}

move_file() {
    local source="$1" destination="$2" name="${1##*/}"
    [[ -f "$source" && ! -L "$source" && -n "$destination" ]] || return 0
    # Never move an active standalone .sh script.
    if [[ -e "$SCRIPT_PATH" && "$source" -ef "$SCRIPT_PATH" ]]; then return 0; fi
    if [[ -d "$destination" && "${source%/*}" -ef "$destination" ]]; then return 0; fi
    local target="$destination/$name"
    if [[ "$OVERWRITE_FILES" == 1 ]]; then
        # Never replace a symlink, directory, FIFO, socket, or other special file.
        if [[ -e "$target" || -L "$target" ]]; then
            [[ -f "$target" && ! -L "$target" ]] || return 0
            [[ "$source" -ef "$target" ]] && return 0
        fi
    else
        [[ ! -e "$target" && ! -L "$target" ]] || return 0
    fi
    if ! mkdir -p -- "$destination"; then
        printf 'Could not create: %s\n' "$destination" >&2
        return 1
    fi
    if [[ "$OVERWRITE_FILES" == 1 ]]; then
        if mv -f -T -- "$source" "$target" && [[ ! -e "$source" ]]; then
            printf 'Moved (overwrite enabled): %s -> %s\n' "$source" "$target"
        fi
    elif mv -n -- "$source" "$destination/"; then
        # A move under -n can succeed while doing nothing if another process created the name.
        if [[ ! -e "$source" ]]; then
            printf 'Moved: %s -> %s/\n' "$source" "$destination"
        fi
    fi
}

archive_destination() {
    local source="$1" pattern="$2" archive_root="$3"
    local kind="${pattern#*.}" modified now bucket
    # Only patterns beginning *.<type> are allowed for archive rules.
    [[ "$pattern" == \*.* && "$kind" != *'/'* && "$kind" != *'*'* && "$kind" != *'?'* && "$kind" != *'['* ]] || return 1
    modified=$(stat -c %Y -- "$source") || return 1
    now=$(date +%s)
    if (( now - modified >= ARCHIVE_OLD_AFTER )); then bucket=Old; else bucket=New; fi
    printf '%s/%s/%s' "$archive_root" "$bucket" "$kind"
}

apply_rule_to_file() {
    local source="$1" scope="$2" name="${1##*/}" i dest
    for ((i=0; i<rule_count; i++)); do
        [[ "${scopes[i]}" == "$scope" ]] || continue
        [[ "$name" == ${patterns[i]} ]] || continue
        dest="${destinations[i]}"
        if [[ "${modes[i]}" == archive ]]; then
            dest="$(archive_destination "$source" "${patterns[i]}" "$dest")" || continue
        fi
        move_file "$source" "$dest"
        return 0  # First matching rule wins.
    done
}

sort_directory() {
    local directory="$1" scope="$2" source
    [[ -d "$directory" && "$directory" != / && "$directory" != /home ]] || return 0
    for source in "$directory"/*; do
        [[ -f "$source" && ! -L "$source" ]] || continue
        apply_rule_to_file "$source" "$scope"
    done
}

find_saves_dir() {
    local i
    for ((i=0; i<rule_count; i++)); do
        if [[ "${scopes[i]}" == watch && "${patterns[i]}" == '*.sav' && "${modes[i]}" == move ]]; then
            printf '%s' "${destinations[i]}"; return
        fi
    done
    printf '%s/Sorted/Saves' "$HOME"
}

reclassify_archives() {
    local i root kind bucket directory source dest
    for ((i=0; i<rule_count; i++)); do
        [[ "${modes[i]}" == archive ]] || continue
        root="${destinations[i]}"; kind="${patterns[i]#*.}"
        [[ "$kind" != *'/'* && "$kind" != *'*'* && "$kind" != *'?'* && "$kind" != *'['* ]] || continue
        for bucket in New Old LEGACY; do
            if [[ "$bucket" == LEGACY ]]; then directory="$root/$kind"
            else directory="$root/$bucket/$kind"; fi
            [[ -d "$directory" ]] || continue
            for source in "$directory"/*; do
                [[ -f "$source" && ! -L "$source" ]] || continue
                [[ "${source##*/}" == ${patterns[i]} ]] || continue
                dest="$(archive_destination "$source" "${patterns[i]}" "$root")" || continue
                move_file "$source" "$dest"
            done
        done
    done
}

init_directories() {
    # Only seed a new installation. Never overwrite an existing file,
    # including an intentionally empty watched-folder configuration.
    [[ -e "$SORTER_DIRS_FILE" || -L "$SORTER_DIRS_FILE" ]] && return 0
    local parent tmp
    parent="${SORTER_DIRS_FILE%/*}"
    mkdir -p -- "$parent" || return 1
    tmp=$(mktemp "$parent/.directories-XXXXXX") || return 1
    printf '%s\n' '~/Downloads' '~/Documents' > "$tmp"
    if [[ ! -e "$SORTER_DIRS_FILE" && ! -L "$SORTER_DIRS_FILE" ]]; then
        mv -n -- "$tmp" "$SORTER_DIRS_FILE" || true
    fi
    rm -f -- "$tmp"
}

init_rules() {
    [[ -e "$SORTER_RULES_FILE" ]] && return 0
    local parent tmp
    parent="${SORTER_RULES_FILE%/*}"
    mkdir -p -- "$parent" || return 1
    tmp=$(mktemp "$parent/.rules-XXXXXX") || return 1
    # The embedded defaults are identical to the separate config editor's defaults.
    printf '%s\n' "$DEFAULT_RULES" > "$tmp"
    if [[ ! -e "$SORTER_RULES_FILE" ]]; then
        mv -n -- "$tmp" "$SORTER_RULES_FILE" || true
    fi
    rm -f -- "$tmp"
}

init_directories || exit 1
init_rules || exit 1
printf 'Sorter active; files are checked every %s seconds. Editable rules: %s\n' "$SCAN_INTERVAL" "$SORTER_RULES_FILE"
while true; do
    load_overwrite
    load_rules
    if [[ -r "$SORTER_DIRS_FILE" ]]; then
        while IFS= read -r directory || [[ -n "$directory" ]]; do
            # Tilde is a literal in config files, so explicitly expand it.
            # Absolute paths outside $HOME remain valid (including mounted drives).
            directory="$(expand_path "$directory")" || continue
            [[ "$directory" == /* && -d "$directory" ]] || continue
            if [[ "$directory" == "$HOME" ]]; then sort_directory "$directory" home
            else sort_directory "$directory" watch; fi
        done < "$SORTER_DIRS_FILE"
    fi
    sort_directory "$(find_saves_dir)" saves
    reclassify_archives
    sleep "$SCAN_INTERVAL"
done
