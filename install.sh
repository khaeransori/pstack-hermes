#!/usr/bin/env bash
# Build pstack for Hermes and link it into place:
#   ~/.hermes/pstack                                  the full tree (skills, agents, guide, adapter)
#   ~/.hermes/skills/software-development/pstack      one router skill in the Hermes index
set -euo pipefail
cd "$(dirname "$0")"
home="${HERMES_HOME:-$HOME/.hermes}"
tree="$home/pstack"
skill="$home/skills/software-development/pstack"
python3 generate.py
python3 generate.py --check
for link in "$tree" "$skill"; do
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    echo "$link exists and is not a symlink; move it away first" >&2
    exit 1
  fi
done
mkdir -p "$(dirname "$tree")" "$(dirname "$skill")"
ln -sfn "$PWD/dist" "$tree"
ln -sfn "$PWD/dist/router" "$skill"
echo "linked $tree and $skill"
