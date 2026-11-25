#!/usr/bin/env bash
# End-to-end smoke test on the bundled synthetic Operations Management PDF (8 pages, EOQ / ROP / ABC).
# Builds into a throwaway studio folder, so your real ~/MBA-Studio is untouched.
#   bash tests/smoke.sh            KEEP=1 keeps the output folder
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(dirname "$HERE")"
PY="$SKILL/../../kit/.venv/bin/python"
export MBA_STUDIO_HOME="${MBA_STUDIO_HOME_TEST:-$(mktemp -d)/MBA-Studio}"
"$PY" "$SKILL/studio/studio.py" new "$HERE/OM_Unit3_Inventory_TEST.pdf" --subject "Operations Management"
P="$MBA_STUDIO_HOME/Operations_Management/OM_Unit3_Inventory_TEST"
cp "$HERE/example_project/outline.json" "$P/"
mkdir -p "$P/specs" && cp "$HERE"/example_project/specs/*.json "$P/specs/"
"$PY" "$SKILL/studio/studio.py" check "$P"
"$PY" "$SKILL/studio/studio.py" approve "$P" --by "smoke test (synthetic fixture)"
"$PY" "$SKILL/studio/studio.py" all "$P"
grep -m1 "^Status" "$P/qc/qc_report.md"
echo "output: $P"
[ "${KEEP:-0}" = 1 ] || echo "(set KEEP=1 to keep it; it is in a temp folder)"
