#!/usr/bin/env bash
# Double-click to deploy banks v11 into the Unitty landings repo.
set -euo pipefail

REPO="$HOME/Documents/GitHub/unitty-solutions-landing"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">>> banks v11 deploy"
echo "--- repo:    $REPO"
echo "--- source:  $HERE"

if [ ! -d "$REPO/landings" ]; then
  echo "*** could not find the clone at $REPO/landings — edit this script's REPO= line"
  read -n1 -p "press any key to close..."
  exit 1
fi

echo "--- copying files"
cp -v "$HERE/landings/banks.page.html"           "$REPO/landings/banks.page.html"
cp -v "$HERE/landings/banks.json"                "$REPO/landings/banks.json"
cp -v "$HERE/public/banks/index.html"            "$REPO/public/banks/index.html"
cp -v "$HERE/public/logos/banks/tbc.png"         "$REPO/public/logos/banks/tbc.png"
cp -v "$HERE/public/logos/banks/bog.png"         "$REPO/public/logos/banks/bog.png"
cp -v "$HERE/public/logos/banks/nbg.png"         "$REPO/public/logos/banks/nbg.png"

echo "--- removing placeholder SVGs"
rm -f "$REPO/public/logos/banks/tbc.svg" "$REPO/public/logos/banks/bog.svg" "$REPO/public/logos/banks/nbg.svg"

echo "+++ v11 files in place"
echo ""
echo "<<< NEXT: open GitHub Desktop → review changes → commit with title:"
echo ""
echo "    banks: v11 - real TBC/BOG/NBG logos + hero rewrite + stats centered + \"20 წუთი, 100+ საათი\""
echo ""
echo "    then push. cloudflare pages will rebuild in ~1-2 minutes."
echo ""
read -n1 -p "press any key to close..."
