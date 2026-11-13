#!/usr/bin/env bash
set -euo pipefail
REPO="$HOME/Documents/GitHub/unitty-solutions-landing"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo ">>> banks v13 deploy"
if [ ! -d "$REPO/landings" ]; then
  echo "*** clone not at $REPO — edit REPO= in this file"; read -n1 -p "press any key..."; exit 1
fi
cp -v "$HERE/landings/banks.page.html"   "$REPO/landings/banks.page.html"
cp -v "$HERE/landings/banks.json"        "$REPO/landings/banks.json"
cp -v "$HERE/public/banks/index.html"    "$REPO/public/banks/index.html"
cp -v "$HERE/public/logos/banks/tbc.png" "$REPO/public/logos/banks/tbc.png"
cp -v "$HERE/public/logos/banks/bog.png" "$REPO/public/logos/banks/bog.png"
cp -v "$HERE/public/logos/banks/nbg.png" "$REPO/public/logos/banks/nbg.png"
rm -f "$REPO/public/logos/banks/tbc.svg" "$REPO/public/logos/banks/bog.svg" "$REPO/public/logos/banks/nbg.svg"
echo ""
echo "+++ v13 in place. GitHub Desktop → Commit → Push."
echo "    title: banks: v13 - hero copy: plural ავტომატიზაციები + 5+ saati/week promise"
read -n1 -p "press any key..."
