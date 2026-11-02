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
        osv_scanner)
            expected_sha="037c3543ac60359190459b10fbb5331568b4c8f5"
            marker="google/osv-scanner@"; pattern="google/osv-scanner@$expected_sha" ;;
        trivy_action)
            expected_sha="915b19bbe73b92a6cf82a1bc12b087c9a19a5fe2"
            marker="aquasecurity/trivy-action@"; pattern="aquasecurity/trivy-action@$expected_sha" ;;
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
