#!/usr/bin/env bash
# Guard the version pins that Dependabot cannot reach (they sit inside shell
# commands). Single source of truth: scripts/tool-versions.cfg. Every copy of
# each workflow must match it; scripts/check-workflows-sync.sh keeps the pair
# itself identical. Run from anywhere:  bash scripts/check-tool-versions.sh
set -euo pipefail
cd "$(dirname "$0")/.."
status=0
while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"                       # drop trailing comments
    [ -z "${line// }" ] && continue          # skip blanks/comment-only lines
    name="${line%%:*}"
    version="${line#*:}"
    name="$(echo "$name" | tr -d ' \t')"
    version="$(echo "$version" | tr -d ' \t\"')"
    case "$name" in
        gitleaks) marker="GITLEAKS_VERSION:"; pattern="GITLEAKS_VERSION: $version" ;;
        semgrep)  marker="semgrep=="; pattern="semgrep==$version" ;;
        *) echo "? no known check for '$name'"; status=1; continue ;;
    esac
    found=0
    for f in workflows/*.yml .github/workflows/*.yml; do
        if grep -qF "$marker" "$f"; then
            found=1
            if grep -qF "$pattern" "$f"; then
                echo "✓ $f: $name $version"
            else
                echo "✗ $f: $name does not match scripts/tool-versions.cfg ($version)"
                status=1
            fi
        fi
    done
    [ "$found" = 1 ] || { echo "✗ no workflow references $name at all"; status=1; }
done < scripts/tool-versions.cfg
exit $status
