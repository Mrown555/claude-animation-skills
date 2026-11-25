# MBA Animation Studio (`/mba-lesson`)

An addition to [claude-animation-skills](https://github.com/artemnovitckii/claude-animation-skills) by Artem Novitckii (MIT). It turns MBA lecture-note PDFs into narrated 1920×1080, 30 fps animated lessons plus study documents. The original 11 skills, `kit/`, `install.sh`, the README and the LICENSE are unchanged. Everything MBA-specific lives in this folder, and `install.sh` links it as `/mba-lesson`.

## What you get per PDF
```
~/MBA-Studio/<Subject>/<PDF name>/
  00_<PDF>_complete.mp4 (+ .srt, chapters)   lessons/Lnn_<title>.mp4 (+ .srt)
  scripts/narration_script.md                reference/page_index.pdf, reference/formulas_and_definitions.pdf
  revision_notes.pdf   practice_questions.pdf   answer_key.pdf
  qc/qc_report.md   qc/contact_sheets/Lnn.jpg
  outline.json (approved)   specs/Lnn.json   source/<pdf>   .build/ (work files, safe to delete)
```

## How it works
```
PDF → ingest.py (text + page images + tables + flags, every page)
    → outline.json (written by Claude, validated: every page accounted for) → user approval (hash-locked)
    → specs/Lnn.json (scenes + narration + vars) → calc.py (exact maths, {{placeholders}}, checks against the PDF)
    → voice.py (Kokoro per sentence, cached; timing, subtitles, SFX, ducked music bed)
    → engine16x9 (DOM/SVG/KaTeX/canvas scenes, frame = f(t)) → render.js (Playwright frame-stepper, ≤4 workers,
      static holds reused, unchanged scenes cached) → ffmpeg (lesson MP4 + SRT → complete MP4 with chapters)
    → docs.py (PDFs via Chromium) → qc.py (report + contact sheets)
```
Reused from the original repo: the Playwright → ffmpeg frame-stepper approach and the stick-figure rig (`lib.js`/`chars.js`, loaded unchanged for `roleplay`), kit fonts, kit Playwright, the Kokoro voice setup, and the synthesized SFX (ported into `voice.py`). HyperFrames stays installed for the original skills; it isn't used here.

| File | Role |
|---|---|
| `SKILL.md` | the workflow Claude follows for `/mba-lesson` |
| `guides/` | outline schema, scene catalogue, teaching rules |
| `studio/` | Python pipeline (`studio.py` is the CLI) |
| `engine16x9/` | 16:9 engine: `engine.js` core, `scenes/*.js`, `render.js`, `pdf.js`, vendored KaTeX (MIT) |
| `tests/` | synthetic 8-page Operations Management PDF, its approved outline and specs, `smoke.sh` |
| `DEVLOG.md` | development log, test results, known limitations |

Install on Windows: see `INSTALL_WINDOWS.md`. Credits: KaTeX (MIT), Kokoro (Apache-2.0) via kokoro-onnx, Playwright, ffmpeg, poppler, pdfplumber; fonts as in `kit/fonts` (OFL).
