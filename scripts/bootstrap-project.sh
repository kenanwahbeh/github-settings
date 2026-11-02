#!/usr/bin/env bash
set -euo pipefail

preset="${1:?preset is required}"
source_dir="presets/${preset}"

case "$preset" in
    generic|python|nextjs|cloudflare-worker) ;;
    *) echo "Unsupported preset: $preset" >&2; exit 2 ;;
esac

if [[ ! -d "$source_dir" ]]; then
    echo "Missing preset directory: $source_dir" >&2
    exit 1
fi

cp "$source_dir/project.yml" project.yml
if [[ -f "$source_dir/README.md" ]]; then
    cp "$source_dir/README.md" README.md
fi
