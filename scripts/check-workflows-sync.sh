#!/usr/bin/env bash
# Consistency check: workflows/ holds the templates that apply.py tells other
# repositories to copy; .github/workflows/ is this repository's own running
# copy. The pairs must stay identical (see README.md (model repository section)).
# Run from anywhere:  bash scripts/check-workflows-sync.sh   (exit 0 = in sync)
set -euo pipefail
cd "$(dirname "$0")/.."
status=0
for pair in secrets semgrep; do
    if ! diff -q "workflows/${pair}.yml" ".github/workflows/${pair}.yml" >/dev/null; then
        echo "✗ drift: workflows/${pair}.yml != .github/workflows/${pair}.yml"
        diff -u "workflows/${pair}.yml" ".github/workflows/${pair}.yml" || true
        status=1
    else
        echo "✓ ${pair}.yml in sync"
    fi
done
exit $status
