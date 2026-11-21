#!/usr/bin/env bash
# Print the next release tag: v<pstack version>-hermes.<N>, N = highest existing N for that version + 1.
# Reads the version from dist/UPSTREAM.json, so run python3 generate.py first.
set -euo pipefail
cd "$(dirname "$0")"
version=$(python3 -c 'import json; print(json.load(open("dist/UPSTREAM.json"))["pstack_version"])')
last=$(git tag -l "v${version}-hermes.*" | sed "s/^v${version}-hermes\.//" | { grep -E '^[0-9]+$' || true; } | sort -n | tail -1)
echo "v${version}-hermes.$(( ${last:-0} + 1 ))"
