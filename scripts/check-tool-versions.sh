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
    # For SHA-pinned actions, we validate the SHA directly against known-good values.
    # tool-versions.cfg stores "name: version" and a separate mapping in this script
    # resolves version -> expected SHA. The workflow must contain that exact SHA.
    case "$name" in
        gitleaks) marker="GITLEAKS_VERSION:"; pattern="GITLEAKS_VERSION: $version" ;;
        gitleaks_sha256) marker="GITLEAKS_SHA256:"; pattern="GITLEAKS_SHA256: $version" ;;
        semgrep)  marker="semgrep=="; pattern="semgrep==$version" ;;
        actionlint) marker="ACTIONLINT_VERSION:"; pattern="ACTIONLINT_VERSION: $version" ;;
        actionlint_sha256) marker="ACTIONLINT_SHA256:"; pattern="ACTIONLINT_SHA256: $version" ;;
        osv_scanner) marker="OSV_VERSION:"; pattern="OSV_VERSION: \"$version\"" ;;
        osv_scanner_digest) marker="OSV_IMAGE:"; pattern="OSV_IMAGE: \"ghcr.io/google/osv-scanner@sha256:$version\"" ;;
        trivy) marker="TRIVY_VERSION:"; pattern="TRIVY_VERSION: \"$version\"" ;;
        trivy_digest) marker="TRIVY_IMAGE:"; pattern="TRIVY_IMAGE: \"aquasec/trivy@sha256:$version\"" ;;
        mutmut) marker="mutmut=="; pattern="mutmut==$version" ;;
        benchmark_action)
            expected_sha="49efc295c639840069791d8d1f47a24b5e8c7f34"
            marker="benchmark-action/github-action-benchmark@"; pattern="benchmark-action/github-action-benchmark@$expected_sha" ;;
        pre_commit_action)
            expected_sha="2c7b3805fd2a0fd8c1884dcaebf91fc102a13ecd"
            marker="pre-commit/action@"; pattern="pre-commit/action@$expected_sha" ;;
        *) echo "? no known check for '$name'"; status=1; continue ;;
    esac
    found=0
    for f in workflows/*.yml .github/workflows/*.yml; do
        if grep -qF "$marker" "$f"; then
            found=1
            marker_lines="$(grep -F "$marker" "$f")"
            unexpected="$(printf '%s\n' "$marker_lines" | grep -Fv "$pattern" || true)"
            if [ -z "$unexpected" ]; then
                echo "✓ $f: $name $version"
            else
                echo "✗ $f: every $name reference must match scripts/tool-versions.cfg ($version)"
                printf '%s\n' "$unexpected"
                status=1
            fi
        fi
    done
    [ "$found" = 1 ] || { echo "✗ no workflow references $name at all"; status=1; }
done < scripts/tool-versions.cfg
exit $status
