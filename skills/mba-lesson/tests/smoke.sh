#!/usr/bin/env bash
# End-to-end smoke test on the bundled synthetic Operations Management PDF (8 pages, EOQ / ROP / ABC).
# Builds into ~/MBA-Studio-test (kept between runs, so an interrupted run resumes and finished scenes are not rebuilt);
# your real ~/MBA-Studio is untouched.
#   bash tests/smoke.sh                      clean (light) style
#   STYLE=kurzgesagt bash tests/smoke.sh     Kurzgesagt-style space theme
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(dirname "$HERE")"
PY="$SKILL/../../kit/.venv/bin/python"
export MBA_STUDIO_HOME="${MBA_STUDIO_HOME_TEST:-$HOME/MBA-Studio-test}"
"$PY" "$SKILL/studio/studio.py" new "$HERE/OM_Unit3_Inventory_TEST.pdf" --subject "Operations Management"
P="$MBA_STUDIO_HOME/Operations_Management/OM_Unit3_Inventory_TEST"
cp "$HERE/example_project/outline.json" "$P/"
if [ -n "${STYLE:-}" ]; then "$PY" -c "import json,sys;f=sys.argv[1];m=json.load(open(f));m['style']=sys.argv[2];json.dump(m,open(f,'w'),indent=1)" "$P/project.json" "$STYLE"; echo "style: $STYLE"; fi
mkdir -p "$P/specs" && cp "$HERE"/example_project/specs/*.json "$P/specs/"
"$PY" "$SKILL/studio/studio.py" check "$P"
"$PY" "$SKILL/studio/studio.py" approve "$P" --by "smoke test (synthetic fixture)"
"$PY" "$SKILL/studio/studio.py" all "$P"
grep -m1 "^Status" "$P/qc/qc_report.md"
echo "output: $P"
echo "complete video: $P/00_OM_Unit3_Inventory_TEST_complete.mp4"
