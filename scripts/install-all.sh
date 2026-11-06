#!/usr/bin/env bash
# Link this repo's skills into every known agent skills directory on this machine.
# Source stays in the repo; nothing is copied.
#
#   ./install-all.sh                 link all skills
#   ./install-all.sh --dry-run       show what would happen
#   ./install-all.sh -n de-jargon    only this skill
#   ./install-all.sh --uninstall     remove the symlinks

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0
UNINSTALL=0
NAMES=()

usage() {
    sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name)  IFS=',' read -r -a _n <<< "$2"; NAMES+=("${_n[@]}"); shift 2 ;;
        --uninstall) UNINSTALL=1; shift ;;
        --dry-run)   DRY_RUN=1; shift ;;
        -h|--help)   usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done

# Skills = top-level directories that contain SKILL.md
if [[ ${#NAMES[@]} -eq 0 ]]; then
    while IFS= read -r p; do
        NAMES+=("$(basename "$(dirname "$p")")")
    done < <(find "$REPO" -maxdepth 2 -name SKILL.md -not -path "*/node_modules/*")
fi

if [[ ${#NAMES[@]} -eq 0 ]]; then
    echo "no skill found (no SKILL.md in repo root dirs)" >&2
    exit 1
fi

shopt -s nullglob dotglob
targets=()
for d in "$HOME"/.[!.]*/ "$HOME"/*/; do
    [[ -d "${d}skills" ]] && targets+=("${d}skills")
    for e in "${d}"*/; do
        [[ -d "${e}skills" ]] && targets+=("${e}skills")
    done
done
shopt -u nullglob dotglob

# Skip plugin caches and nested skills/skills — not load points
filtered=()
for t in "${targets[@]}"; do
    case "$t" in
        *connectors*|*marketplace*|*/skills/skills*|*.astrbot*) continue ;;
    esac
    filtered+=("$t")
done

# dedupe
mapfile -t filtered < <(printf '%s\n' "${filtered[@]}" | sort -u)

echo "repo:     $REPO"
echo "skills:   ${NAMES[*]}"
echo "targets:  ${#filtered[@]}"
echo ""

created=0; removed=0; skipped=0; failed=0

for name in "${NAMES[@]}"; do
    src="$REPO/$name"
    for dir in "${filtered[@]}"; do
        link="$dir/$name"
        short="${link/#$HOME/~}"

        if [[ $UNINSTALL -eq 1 ]]; then
            if [[ ! -L "$link" ]]; then
                skipped=$((skipped+1)); continue
            fi
            if [[ $DRY_RUN -eq 1 ]]; then
                echo "  would remove: $short"; removed=$((removed+1)); continue
            fi
            rm -f "$link"; removed=$((removed+1)); continue
        fi

        if [[ -e "$link" || -L "$link" ]]; then
            skipped=$((skipped+1)); continue
        fi

        if [[ $DRY_RUN -eq 1 ]]; then
            echo "  would create: $short"; created=$((created+1)); continue
        fi

        if ln -s "$src" "$link" 2>/dev/null; then
            created=$((created+1))
        else
            echo "  failed: $short" >&2; failed=$((failed+1))
        fi
    done
done

echo ""
if [[ $UNINSTALL -eq 1 ]]; then
    echo "removed $removed, skipped $skipped, failed $failed"
else
    echo "created $created, existing $skipped, failed $failed"
fi
[[ $DRY_RUN -eq 1 ]] && echo "(dry run, nothing changed)"
exit 0
