#!/usr/bin/env bash
# MBA Animation Studio setup. Checks first, installs only what is missing, then verifies each part.
#   bash skills/mba-lesson/setup.sh            (from anywhere; safe to run again)
# Uses the repo's own kit: kit/node_modules (Playwright), kit/.venv (Kokoro voice), kit/models.
# Does not download the Parakeet word-timing model (only the original /stick-figure and /zach-d-films skills need it).
set -euo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT="$(cd "$SKILL/../../kit" && pwd)"
ok() { printf '  \033[32mok\033[0m  %s\n' "$*"; }
miss() { printf '  \033[31mmissing\033[0m  %s\n' "$*"; }
say() { printf '\033[1m%s\033[0m\n' "$*"; }
fail=0

say "1. system tools"
for t in ffmpeg ffprobe node npm python3 pdfinfo pdftotext pdftoppm; do
  if command -v "$t" >/dev/null; then ok "$t ($(command -v "$t"))"; else miss "$t"; fail=1; fi
done
case "$(command -v node || true)" in /mnt/*) miss "node resolves to Windows ($(command -v node)); install Linux Node 22 inside WSL (see INSTALL_WINDOWS.md)"; fail=1;; esac
if [ $fail = 1 ]; then
  echo; echo "Install the missing tools first (Ubuntu/WSL):"
  echo "  sudo apt update && sudo apt install -y ffmpeg python3-venv python3-pip poppler-utils"
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { miss "python 3.9+"; exit 1; }

say "2. Node packages (kit/node_modules: Playwright + Chromium, shared with the original skills)"
if [ -d "$KIT/node_modules/playwright" ]; then ok "Playwright already installed"; else
  say "   running the repo's kit/setup.sh (Playwright, Chromium, three.js, GSAP, HyperFrames)"; bash "$KIT/setup.sh"; fi

say "3. Python voice environment (kit/.venv)"
[ -x "$KIT/.venv/bin/python" ] || python3 -m venv "$KIT/.venv"
need=""
for m in numpy scipy soundfile kokoro_onnx pdfplumber; do
  "$KIT/.venv/bin/python" -c "import $m" 2>/dev/null && ok "$m" || need="$need $m"
done
if [ -n "$need" ]; then
  pk=$(echo "$need" | sed 's/kokoro_onnx/kokoro-onnx/')
  say "   installing:$pk"; "$KIT/.venv/bin/python" -m pip install -q $pk
fi

say "4. Kokoro voice models (~340 MB, once)"
mkdir -p "$KIT/models"
[ -s "$KIT/models/kokoro-v1.0.onnx" ] && ok "kokoro-v1.0.onnx" || curl -fL -o "$KIT/models/kokoro-v1.0.onnx" https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s "$KIT/models/voices-v1.0.bin" ] && ok "voices-v1.0.bin" || curl -fL -o "$KIT/models/voices-v1.0.bin" https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

say "5. verify"
[ -s "$SKILL/engine16x9/vendor/katex/katex.min.js" ] && ok "KaTeX (vendored)" || { miss "engine16x9/vendor/katex"; exit 1; }
"$KIT/.venv/bin/python" - <<EOF && ok "Kokoro speaks" || { miss "Kokoro test failed"; exit 1; }
from kokoro_onnx import Kokoro
k = Kokoro("$KIT/models/kokoro-v1.0.onnx", "$KIT/models/voices-v1.0.bin")
a, sr = k.create("Setup check.", voice="am_michael", speed=1.0, lang="en-us")
assert len(a) > sr * 0.3
EOF
if NODE_PATH="$KIT/node_modules" node -e "require('playwright').chromium.launch().then(b=>b.close())" 2>/tmp/studio_pw.txt; then ok "headless Chromium starts"; else
  miss "Chromium could not start:"; tail -3 /tmp/studio_pw.txt
  echo "  fix:  cd \"$KIT\" && sudo env \"PATH=\$PATH\" npx playwright install-deps chromium"; exit 1; fi
say "ready. Next:  \"$KIT/.venv/bin/python\" \"$SKILL/studio/studio.py\" new <your.pdf> --subject \"<Subject>\""
