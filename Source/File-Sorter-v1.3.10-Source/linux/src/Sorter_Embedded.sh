#!/usr/bin/env bash
# File Sorter v1.3.10. Editable rules, folders, destinations and scan interval.
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
SORTER_SCAN_INTERVAL_FILE="${SORTER_SCAN_INTERVAL_FILE:-$CONFIG_DIR/scan-interval.txt}"
SORTER_DESTINATION_MODE_FILE="${SORTER_DESTINATION_MODE_FILE:-$CONFIG_DIR/destination-mode.txt}"
DESTINATION_MODE=shared
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

declare -a scopes patterns destinations modes priorities sources recursive_flags sorted_indices
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
    local scope pattern destination mode priority source_list recursive extra realdest line
    scopes=(); patterns=(); destinations=(); modes=(); priorities=(); sources=(); recursive_flags=(); sorted_indices=(); rule_count=0
    if [[ ! -r "$SORTER_RULES_FILE" ]]; then
        printf 'Warning: no rules file: %s\n' "$SORTER_RULES_FILE" >&2
        return 1
    fi
    local positional=0
    grep -qF "# rule-order: position; first listed rule wins" "$SORTER_RULES_FILE" && positional=1
    # Four legacy columns remain valid. New rules store position-rank and a source
    # folder list; '-' means use all main watched directories.
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" == \#* || -z "$line" ]] && continue
        IFS=$'\t' read -r scope pattern destination mode priority source_list recursive extra <<< "$line"
        [[ -z "$extra" ]] || continue
        [[ "$scope" == watch || "$scope" == home || "$scope" == saves ]] || continue
        [[ "$mode" == move || "$mode" == archive ]] || continue
        [[ -n "$pattern" && -n "$destination" ]] || continue
        [[ "$pattern" != */* && "$pattern" != *$'\n'* ]] || continue
        [[ "$destination" != *$'\n'* && "$destination" != *$'\r'* ]] || continue
        if [[ "$mode" == archive && "$pattern" != \*.* ]]; then continue; fi
        realdest="$(expand_path "$destination")" || continue
        [[ "$realdest" != / && "$realdest" != "$HOME" ]] || continue
        [[ -n "$priority" ]] || priority=0
        [[ "$priority" =~ ^[0-9]{1,4}$ ]] || continue
        (( 10#$priority <= 9999 )) || continue
        [[ -n "$source_list" ]] || source_list='-'
        [[ -n "$recursive" ]] || recursive=0
        [[ "$recursive" == 0 || "$recursive" == 1 ]] || continue
        if [[ "$source_list" != '-' ]]; then
            [[ "$scope" == watch && "$source_list" != *$'\n'* && "$source_list" != *$'\t'* ]] || continue
            local -a source_folders
            IFS='|' read -ra source_folders <<< "$source_list"
            (( ${#source_folders[@]} <= 32 )) || continue
            local raw valid=1
            for raw in "${source_folders[@]}"; do
                [[ -n "$raw" ]] || { valid=0; break; }
                local expanded
                expanded="$(expand_path "$raw")" || { valid=0; break; }
                [[ "$expanded" != / && "$expanded" != /home && "$expanded" != /run ]] || { valid=0; break; }
            done
            ((valid)) || continue
        fi
        scopes+=("$scope"); patterns+=("$pattern"); destinations+=("$realdest"); modes+=("$mode")
        priorities+=("$((10#$priority))"); sources+=("$source_list"); recursive_flags+=("$recursive")
        sorted_indices+=("$rule_count")
        ((rule_count+=1))
    done < "$SORTER_RULES_FILE"
    # Legacy priorities are migrated logically, until Config saves position-rank rules.
    # In new files the first listed rule always wins regardless of numeric column.
    local a b key
    if (( !positional )); then
        for ((a=1;a<rule_count;a++));do
            key="${sorted_indices[a]}";b=$((a-1))
            while (( b>=0 && priorities[${sorted_indices[b]}] < priorities[key] ));do
                sorted_indices[b+1]="${sorted_indices[b]}"
                ((b-=1))
            done
            sorted_indices[b+1]="$key"
        done
    fi
}

source_matches_rule() {
    local index="$1" watched="$2" raw expanded
    [[ "${sources[index]}" != '-' ]] || return 1
    local -a entries
    IFS='|' read -ra entries <<< "${sources[index]}"
    for raw in "${entries[@]}";do
        expanded="$(expand_path "$raw")" || continue
        [[ "$expanded" == "$watched" ]] && return 0
    done
    return 1
}

load_scan_interval() {
    # Reload on every scan. Reject empty, negative, zero and non-decimal input.
    # A missing/malformed value preserves the historical 2-second default.
    SCAN_INTERVAL=2
    local setting=''
    if [[ -f "$SORTER_SCAN_INTERVAL_FILE" && ! -L "$SORTER_SCAN_INTERVAL_FILE" ]]; then
        IFS= read -r setting < "$SORTER_SCAN_INTERVAL_FILE" || true
        if (( ${#setting} <= 48 )) && [[ "$setting" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] && [[ "$setting" =~ [1-9] ]]; then
            SCAN_INTERVAL="$setting"
        fi
    fi
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

load_destination_mode() {
    DESTINATION_MODE=shared
    local setting=''
    if [[ -f "$SORTER_DESTINATION_MODE_FILE" && ! -L "$SORTER_DESTINATION_MODE_FILE" ]]; then
        IFS= read -r setting < "$SORTER_DESTINATION_MODE_FILE" || true
        [[ "$setting" == per-folder ]] && DESTINATION_MODE=per-folder
    fi
}

resolve_destination() {
    # Remap only paths beneath the conventional ~/Sorted root; other user
    # destinations, including external drives, keep their exact meaning.
    local destination="$1" watched="$2" common="$HOME/Sorted"
    if [[ "$DESTINATION_MODE" == per-folder && "$watched" != "$HOME" &&
          ( "$destination" == "$common" || "$destination" == "$common/"* ) ]]; then
        printf '%s/Sorted%s' "$watched" "${destination#"$common"}"
    else
        printf '%s' "$destination"
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
    local source="$1" scope="$2" watched="$3" global_watch="${4:-1}" nested="${5:-0}" name="${1##*/}" i order dest
    for order in "${sorted_indices[@]}"; do
        i="$order"
        [[ "$nested" == 0 || "${recursive_flags[i]}" == 1 ]] || continue
        if [[ "${sources[i]}" == '-' ]]; then
            [[ "${scopes[i]}" == "$scope" && "$global_watch" == 1 ]] || continue
        else
            [[ "${scopes[i]}" == watch ]] || continue
            source_matches_rule "$i" "$watched" || continue
        fi
        [[ "$name" == ${patterns[i]} ]] || continue
        dest="$(resolve_destination "${destinations[i]}" "$watched")"
        if [[ "${modes[i]}" == archive ]]; then
            dest="$(archive_destination "$source" "${patterns[i]}" "$dest")" || continue
        fi
        move_file "$source" "$dest"
        return 0  # First matching rule by displayed list position wins.
    done
}

# Preserve the source root when evaluating per-rule folders and per-folder output.
# Files already under any configured output root must never be ingested again.
output_path_for_watched() {
    local file="$1" watched="$2" i target
    for ((i=0;i<rule_count;i++)); do
        target="$(resolve_destination "${destinations[i]}" "$watched")"
        if [[ "$file" == "$target" || "$file" == "$target/"* ]]; then return 0; fi
    done
    return 1
}

sort_directory() {
    local directory="$1" scope="$2" global_watch="${3:-1}" source i recursive_needed=0
    [[ -d "$directory" && "$directory" != / && "$directory" != /home ]] || return 0
    for source in "$directory"/*; do
        [[ -f "$source" && ! -L "$source" ]] || continue
        output_path_for_watched "$source" "$directory" && continue
        apply_rule_to_file "$source" "$scope" "$directory" "$global_watch" 0
    done
    for ((i=0;i<rule_count;i++)); do
        [[ "${recursive_flags[i]}" == 1 ]] || continue
        if [[ "${sources[i]}" == '-' ]]; then
            [[ "${scopes[i]}" == "$scope" && "$global_watch" == 1 ]] || continue
        else
            [[ "${scopes[i]}" == watch ]] || continue
            source_matches_rule "$i" "$directory" || continue
        fi
        recursive_needed=1;break
    done
    ((recursive_needed)) || return 0
    # Find does not follow symlink directories by default. NUL boundaries
    # preserve whitespace and special filenames. In-output files are ignored.
    while IFS= read -r -d '' source; do
        [[ -f "$source" && ! -L "$source" ]] || continue
        output_path_for_watched "$source" "$directory" && continue
        apply_rule_to_file "$source" "$scope" "$directory" "$global_watch" 1
    done < <(find -H "$directory" -mindepth 2 -type f -print0 2>/dev/null)
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

reclassify_archive_root() {
    local i="$1" root="$2" kind="${patterns[$1]#*.}" bucket directory source dest
    [[ "$kind" != *'/'* && "$kind" != *'*'* && "$kind" != *'?'* && "$kind" != *'['* ]] || return 0
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
}

reclassify_archives() {
    local i root watched
    for ((i=0; i<rule_count; i++)); do
        [[ "${modes[i]}" == archive ]] || continue
        root="${destinations[i]}"
        if [[ "$DESTINATION_MODE" == per-folder && ( "$root" == "$HOME/Sorted" || "$root" == "$HOME/Sorted/"* ) ]]; then
            if [[ "${sources[i]}" == '-' ]]; then
                if [[ -r "$SORTER_DIRS_FILE" ]]; then
                    while IFS= read -r watched || [[ -n "$watched" ]]; do
                        watched="$(expand_path "$watched")" || continue
                        [[ "$watched" == /* && -d "$watched" ]] || continue
                        reclassify_archive_root "$i" "$(resolve_destination "$root" "$watched")"
                    done < "$SORTER_DIRS_FILE"
                fi
            else
                local -a custom
                IFS='|' read -ra custom <<< "${sources[i]}"
                for watched in "${custom[@]}"; do
                    watched="$(expand_path "$watched")" || continue
                    [[ -d "$watched" ]] || continue
                    reclassify_archive_root "$i" "$(resolve_destination "$root" "$watched")"
                done
            fi
        else
            reclassify_archive_root "$i" "$root"
        fi
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
    : > "$tmp"
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
printf 'Sorter active; configurable scan interval (default 2 seconds). Editable rules: %s\n' "$SORTER_RULES_FILE"
while true; do
    load_scan_interval
    load_overwrite
    load_destination_mode
    load_rules
    watch_count=0
    if [[ -r "$SORTER_DIRS_FILE" ]]; then
        while IFS= read -r directory || [[ -n "$directory" ]]; do
            # Tilde is a literal in config files, so explicitly expand it.
            # Absolute paths outside $HOME remain valid (including mounted drives).
            directory="$(expand_path "$directory")" || continue
            [[ "$directory" == /* && -d "$directory" ]] || continue
            ((watch_count+=1))
            if [[ "$directory" == "$HOME" ]]; then sort_directory "$directory" home
            else sort_directory "$directory" watch; fi
        done < "$SORTER_DIRS_FILE"
    fi
    # Scan explicit per-rule source folders even if not in directories.txt.
    # A rule with no custom source keeps using the main watched-folders list.
    declare -A scanned
    scanned=()
    if [[ -r "$SORTER_DIRS_FILE" ]]; then
        while IFS= read -r directory || [[ -n "$directory" ]]; do
            directory="$(expand_path "$directory")" || continue
            [[ "$directory" == /* && -d "$directory" ]] || continue
            scanned["$directory"]=1
        done < "$SORTER_DIRS_FILE"
    fi
    for ((i=0;i<rule_count;i++)); do
        [[ "${scopes[i]}" == watch && "${sources[i]}" != '-' ]] || continue
        IFS='|' read -ra rule_dirs <<< "${sources[i]}"
        for rule_dir in "${rule_dirs[@]}"; do
            directory="$(expand_path "$rule_dir")" || continue
            [[ -d "$directory" && "$directory" != / && "$directory" != /home && "$directory" != /run ]] || continue
            [[ "${scanned[$directory]+yes}" ]] && continue
            scanned["$directory"]=1
            ((watch_count+=1))
            sort_directory "$directory" watch 0
        done
    done
    if ((watch_count>0)); then
        sort_directory "$(find_saves_dir)" saves
        reclassify_archives
    fi
    sleep "$SCAN_INTERVAL"
done
