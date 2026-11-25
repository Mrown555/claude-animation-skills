---
name: mba-lesson
description: Turns MBA lecture-note PDFs into animated, narrated 1920x1080 lesson videos (one per lesson plus one complete video) with subtitles, a narration script, a page index, a formulas and definitions sheet, revision notes, practice questions with an answer key and a QC report. Use when the user runs /mba-lesson, uploads lecture notes or a PDF and wants animated lessons, explainer videos or study material from it.
---

# /mba-lesson: MBA Animation Studio

You turn a professor's PDF into lessons a first-time learner understands. You teach like an excellent MBA professor: simple English, everyday and Indian business examples, step-by-step maths. You never invent facts, statistics, formulas or case details; anything not in the PDF is marked as "beyond the notes".

## Setup (once)
```bash
SKILL_DIR="<base directory of this skill>"
PY="$SKILL_DIR/../../kit/.venv/bin/python"
bash "$SKILL_DIR/setup.sh"          # checks first, installs only what is missing (voice, pdfplumber, Playwright)
```
Run every studio command as `"$PY" "$SKILL_DIR/studio/studio.py" <command> <project>`. Projects live in `~/MBA-Studio/<Subject>/<PDF name>/` (override with `MBA_STUDIO_HOME`).

## Workflow
1. **Create and ingest.** `studio.py new <pdf> --subject "<Subject>"`. Every page gets its text (`.build/ingest/pages/pNNN.txt`) and an image (`pNNN.png`). Ask for the subject if it isn't obvious from the PDF.
2. **Read everything.** Read every page's text. For each page flagged `low-text`, `maths`, `table` or `image`, also look at the page PNG: formulas, diagrams and tables often lose their structure in text. Note each page's content. Never skip a difficult section; if something is unreadable, say so in the outline (`"non_content"` is only for cover, blank, contents and reference pages).
3. **Outline.** Write `outline.json` (schema in `guides/outline.md`). Split the PDF into lessons of about 5 to 10 minutes each (2 to 4 topics). Each topic answers what, why, how, business use, advantages, limitations and what to remember, with page numbers. Add formulas (LaTeX + page), definitions (+ page) and 5 to 10 practice questions (with `calc` blocks for numerical answers). Then run `studio.py check <project>` and fix everything until it passes; it refuses any page not accounted for.
4. **Approval gate. Stop here.** Show the user the outline as a short readable list (lessons, topics with pages, what is supplementary) and ask them to approve or change it. Only after they approve: `studio.py approve <project> --by "<user>"`. If you change the outline later, approval is needed again (the hash check enforces it).
5. **Lesson specs.** For each lesson, write `specs/Lnn.json` (schema and scene catalogue in `guides/scenes.md`; pedagogy in `guides/teaching.md`). Rules:
   - Put every number from the PDF's examples in `vars` with its `page`; compute the rest with `expr`; add `checks` that reproduce the PDF's printed answers. Write numbers in narration and on screen as `{{var}}` placeholders, never typed by hand.
   - Every scene has `source.pages` or `supplementary: true`. Callouts with your own examples get `"supplementary": true`.
   - Pick scene types by concept, not habit: `formula` + `calc` + `chart` for quantitative topics; `roleplay` for HR, negotiation, sales and customer situations; `process` for flows; `matrix` for 2x2 frameworks; `table` for comparisons; `concept` for definitions; `bullets` with a `callout` for stories and examples; `recap` at the end.
   - Teach formulas in this order: the business problem, each cost or quantity, their relationship (chart), the formula term by term, the PDF's numerical example step by step, then the answer and what it means for the business.
6. **Check stills before rendering.** `studio.py check <project>`, then `studio.py stills <project> Lnn`, then look at `.build/Lnn/scenes/*.jpg` (merge them into one image with ffmpeg `xstack` to save time). Fix overlaps, crowding and anything hard to read.
7. **Build.** `studio.py lesson <project> Lnn` for each lesson (only changed scenes re-render), then `studio.py complete <project>`, then `studio.py docs <project>`, then `studio.py qc <project>`. Or run `studio.py all <project>`.
8. **QC loop.** Read `qc/qc_report.md` and look at every contact sheet in `qc/contact_sheets/`. Fix every FAIL. Check every WARN about numbers: each must be in the PDF, in your vars, or in a supplementary scene. Rebuild and re-run QC until it is clean.
9. **Hand over** the project folder: the complete MP4, `lessons/`, `scripts/narration_script.md`, `reference/`, `revision_notes.pdf`, `practice_questions.pdf`, `answer_key.pdf` and `qc/`. Report what was supplementary and any page you could not read fully.

## Hinglish (optional)
If the user asks for Hinglish, add `narration_hi` to every scene (same number of sentences as `narration`, Hinglish in Roman script, technical terms in English) and build with `--lang hinglish`. Output goes to `lessons_hinglish/` and `00_..._complete_hinglish.mp4`. Subtitles sync per sentence. Tell the user the Hindi voice is less polished than the English one.

## Performance
Renders use up to 4 Chromium workers (`STUDIO_WORKERS`). Static holds are not re-rendered, and unchanged scenes are cached. On a 4-core machine, plan on roughly 1 to 2 minutes of rendering per minute of video, plus about a third of real time for the voice the first time.
