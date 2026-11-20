#!/usr/bin/env bash
# Build the pstack trees and link one into place.
#   ./install.sh codex    # ~/.codex/pstack + ~/.agents/skills/pstack
#   ./install.sh hermes   # ~/.hermes/pstack + ~/.hermes/skills/software-development/pstack
set -euo pipefail
cd "$(dirname "$0")"
target="${1:-}"
case "$target" in
  codex)
    home="${CODEX_HOME:-$HOME/.codex}"
    tree="$home/pstack"
    skill="$HOME/.agents/skills/pstack"
    ;;
  hermes)
    home="${HERMES_HOME:-$HOME/.hermes}"
    tree="$home/pstack"
    skill="$home/skills/software-development/pstack"
    ;;
  *)
    echo "usage: ./install.sh codex|hermes" >&2
    exit 2
    ;;
esac
python3 generate.py
python3 generate.py --check
for link in "$tree" "$skill"; do
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    echo "$link exists and is not a symlink; move it away first" >&2
    exit 1
  fi
done
mkdir -p "$(dirname "$tree")" "$(dirname "$skill")"
ln -sfn "$PWD/dist/$target" "$tree"
ln -sfn "$PWD/dist/$target/router" "$skill"
echo "linked $tree and $skill"
[ "$target" = codex ] && echo 'Restart Codex, then try: $pstack correct'
exit 0
