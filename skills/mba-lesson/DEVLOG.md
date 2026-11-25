# Development log: MBA Animation Studio

## Fixed decisions (approved by the user)
WSL2 + Ubuntu 24.04 · Playwright frame-stepper + FFmpeg as the only production renderer · HyperFrames kept only for the original skills · Kokoro voice (English; optional Hindi/Hinglish with sentence-level sync) · WSL 8 GB RAM / 8 CPUs / 8 GB swap · at most 4 Chromium workers · 1920×1080, 30 fps · originals untouched, all new work in `skills/mba-lesson/` · page traceability, maths verification, A/V sync and contact-sheet QC · outline approval before rendering.

## Log
**Repository inspection.** 11 skills (10 implementations; `zach-3d-films` is an alias). All are 9:16 with fixed scenes, so I reused their code and approach rather than calling them. Branch `mba-lesson-studio`; the originals stay on git history as the backup, and QC fails if any file outside `skills/mba-lesson/` changes.

**Dependencies (development container, Linux, 4 cores, no GPU).** Checked first: ffmpeg 6.1, Node 22, Python 3.13, poppler and a preinstalled Playwright Chromium were present. Installed only kit/.venv (numpy, scipy, soundfile, kokoro-onnx, pdfplumber) and the two Kokoro model files (~340 MB). KaTeX 0.16.11 is vendored (604 KB) because the CDNs were blocked here and it makes the studio work offline. Parakeet is not downloaded (not needed: we synthesise per sentence, so timing is known exactly).

**Engine.** `engine16x9/engine.js` wraps everything in an IIFE, because the reused `lib.js`/`chars.js` declare globals (`W`, `H`, `clamp`, `ease`). Scenes declare animation spans with `ctx.tw()`. The renderer captures only frames inside spans, plus subtitle changes and fades, and reuses the previous JPEG for static holds.

**Test fixture.** `tests/OM_Unit3_Inventory_TEST.pdf`: 8 synthetic pages written for testing (cover, a blank page, inventory costs, EOQ model, EOQ example, ROP and safety stock, an ABC table, a summary). It is clearly marked as not a professor's material.

**Issues found and fixed during testing**
- Page-number footers ("1/8") were flagged as maths. Footers are now stripped before flagging.
- Variable shadowing in the title scene (element vs time). Fixed.
- Role-play characters inherited the rig's pirate bandana and striped shirt. Now `hat: 'none'` and solid colours.
- Chart curve labels collided, and the y-axis title overlapped tick labels. Now a legend row above the chart, with a wider left margin.
- A 4-step calc scene ran into the subtitle band. With no "given" card and ≥4 steps, the layout is now two columns.
- A 41-word narration sentence (validator warning) was split. Only that one scene re-rendered (cache check).

**Performance (4-core container, CPU only, 4 workers).** L01 is 5.7 min of video and rendered in 2 min 34 s (17% of frames captured; the rest were static holds). First-time voice generation runs at about 3× real time on CPU, and it is cached.

## Known limitations (unresolved)
1. **Hinglish voice quality is unverified by ear.** Kokoro's Hindi voices (`hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi`) generate audio for Romanized Hinglish through the Hindi phonemizer, but nobody has listened to it yet. If it sounds wrong, set `"hinglish_lang": "en-us"` in project.json (Hindi voice, English phonemes) or write `narration_hi` in Devanagari for the Hindi words. Subtitles sync per sentence.
2. **Subtitle chunks inside a sentence** are timed in proportion to their length (sentence boundaries are exact). Good for 1 to 2 chunks; very long sentences may drift by a fraction of a second.
3. **Scanned PDFs:** there is no OCR. Low-text pages are flagged so Claude reads the page image, which works for a few pages. For fully scanned notes, add `tesseract-ocr` (not installed).
4. **No 3D scenes in the 16:9 engine yet.** WebGL in WSL headless Chromium may be software-rendered. The 3D originals (`map-route`, `breakdown`, `zach-d-films`) are untouched and still work at 9:16.
5. **Supply-chain map scene not built yet.** Use `process` (factory → warehouse → retailer) for now.
6. **Lip-sync:** role-play mouths animate while that character's sentence plays; there's no phoneme sync. Both characters share the narrator voice unless a sentence sets `"voice"`.
7. **Performance on the target laptop** (Ryzen 7 4800H, 8 WSL CPUs) is expected to be similar or faster, but it hasn't been measured on that machine.
8. **Teaching quality** depends on Claude following `guides/teaching.md`. The QC checks facts, numbers, layout and sync, not pedagogy. The outline approval step is the human check.

## Acceptance test result (synthetic Operations Management PDF, 8 pages)
Full run with `studio.py all`: **QC PASS**.
1. Every page accounted for: 6 content pages mapped to 5 topics; the cover and the blank page are recorded as non-content.
2. Outline: 2 lessons, 5 topics, 5 formulas, 9 definitions, 5 practice questions; validated and approval-locked.
3. Scripts: 19 scenes and about 130 narration sentences. Supplementary material is labelled on screen ("Beyond the notes") and in the script.
4. Formulas and examples: EOQ built term by term, cost curves with the minimum marked, an inventory sawtooth, ROP on the stock chart, and 3 step-by-step calc scenes. All 26 values recomputed; 8 checks reproduce the PDF's printed answers.
5. Narration and subtitles: A/V drift ≤ 0.02 s, 132 subtitle cues, loudness −17.1 LUFS.
6. and 7. L01 is 5.7 min (26 MB) and L02 4.5 min (19 MB); the complete video is 10.2 min (44 MB) with chapters. 1920×1080, 30 fps, frame counts exact, no black frames.
8. Revision notes, formulas and definitions, page index, practice questions and answer key (answers recomputed).
9. QC report plus 2 contact sheets.
A full rebuild takes 5 min 18 s on a 4-core CPU container (voice cached; about 1 to 2 min of rendering per lesson).

QC false positives found and fixed along the way: a container's default font size counted as text, layout fields (`widths`) counted as content numbers, and KaTeX zero-width spacers counted as 1 px text.
Hinglish: the code path is tested (Hindi voice, sentence sync, frame-exact audio); the sound quality is not yet judged by a human.
