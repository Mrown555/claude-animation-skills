"""Study documents from the approved outline and the lesson specs: narration script, page index, formulas and
definitions sheet, revision notes, practice questions and a separate answer key. Practice answers that carry a
"calc" block are recomputed and must match before anything is written."""
import html
import re

import calc
import ingest
from common import ENGINE, die, load, node_env, run

E = html.escape


def rich(s):
    """**bold**, $tex$ and plain text -> HTML (TeX is typeset by KaTeX in the browser)"""
    out = []
    for part in re.split(r'(\$[^$]+\$)', str(s)):
        if part.startswith('$') and part.endswith('$') and len(part) > 2:
            out.append(f'<span class="tex">{E(part[1:-1])}</span>')
        else:
            out.append(re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', E(part)))
    return ''.join(out)


def page_html(title, subtitle, body):
    k = (ENGINE / 'vendor' / 'katex').as_uri()
    return f"""<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{k}/katex.min.css">
<style>
body{{font:11pt/1.5 'Inter','DejaVu Sans',sans-serif;color:#1b2333}} h1{{font-size:20pt;margin:0}} .sub{{color:#5d6678;margin:4px 0 18px}}
h2{{font-size:14pt;color:#0e7c86;border-bottom:2px solid #0e7c86;padding-bottom:3px;margin-top:22px}} h3{{font-size:12pt;margin:14px 0 4px}}
table{{border-collapse:collapse;width:100%;margin:8px 0}} td,th{{border:1px solid #d9d5cc;padding:5px 8px;vertical-align:top;text-align:left}}
th{{background:#eef6f6}} .pg{{color:#0e7c86;font-size:9pt;white-space:nowrap}} .supp{{color:#b4531f;font-size:9pt;font-weight:600}}
.box{{background:#f6f4ef;border-left:4px solid #0e7c86;padding:8px 12px;margin:8px 0}} .f{{font-size:14pt;padding:6px 0}}
.q{{margin:12px 0;page-break-inside:avoid}} .tag{{display:inline-block;background:#eef6f6;color:#0e7c86;border-radius:9px;padding:0 8px;font-size:9pt}}
li{{margin:2px 0}}
</style></head><body><h1>{E(title)}</h1><div class="sub">{E(subtitle)}</div>{body}
<script src="{k}/katex.min.js"></script>
<script>document.querySelectorAll('.tex').forEach(e=>katex.render(e.textContent,e,{{throwOnError:false,displayMode:e.classList.contains('d')}}))</script>
</body></html>"""


def to_pdf(p, name, title, body):
    src = p.build / 'docs' / (name.replace('/', '_') + '.html')
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(page_html(title, f'{p.meta["subject"]} · {load(p.outline)["title"]}', body), encoding='utf-8')
    out = p.root / f'{name}.pdf'
    out.parent.mkdir(parents=True, exist_ok=True)
    run(['node', ENGINE / 'pdf.js', src, out], env=node_env())
    return out


def pg(x):
    if x.get('supplementary'):
        return '<span class="supp">beyond the notes</span>' + (f' <span class="pg">(method: p. {x["based_on"]})</span>' if x.get('based_on') else '')
    return f'<span class="pg">p. {x.get("page")}</span>'


def verify_practice(o):
    bad = []
    for q in o.get('practice', []):
        c = q.get('calc')
        if not c:
            continue
        try:
            env, _ = calc.solve(c.get('vars', {}))
            v = calc.ev(c['expr'], env)
        except calc.CalcError as e:
            bad.append(f'{q["question"][:50]}: {e}')
            continue
        if abs(v - c['expect']) > max(c.get('tol', 0.01), 1e-9):
            bad.append(f'{q["question"][:50]}: computed {v:.4f}, answer key says {c["expect"]}')
        q['_computed'] = v
    return bad


def make(p):
    o = load(p.outline)
    bad = verify_practice(o)
    if bad:
        die('practice answers do not match the calculation:\n  ' + '\n  '.join(bad))
    ing = load(p.ingest_dir / 'ingest.json')
    made = []
    # narration script (markdown, easy to read and edit)
    md = [f'# Narration script: {o["title"]}', '', f'{p.meta["subject"]}. Source tags show the PDF page each scene teaches from; '
          '"beyond the notes" marks explanations and examples that are not in the original material.', '']
    for s in p.lesson_specs():
        filled, _, _ = calc.apply(load(s), p.meta.get('number_style', 'international'))
        md += [f'## {filled["id"]}: {filled["title"]}', '']
        for i, sc in enumerate(filled['scenes'], 1):
            tag = 'beyond the notes' if sc.get('supplementary') else 'PDF p. ' + ', '.join(map(str, sc.get('source', {}).get('pages', [])))
            md += [f'### Scene {i}: {sc["id"]} ({sc["type"]}) · {tag}', '']
            for ln in sc['narration']:
                md.append(ln if isinstance(ln, str) else ln['text'])
            md.append('')
    sp = p.root / 'scripts' / 'narration_script.md'
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text('\n'.join(md), encoding='utf-8')
    made.append(sp)
    # page index
    use, missing = ingest.coverage(p)
    rows = ''.join(f'<tr><td>p. {i["page"]}</td><td>{"<br>".join(E(x) for x in use[i["page"]]) or "<b>not accounted for</b>"}</td>'
                   f'<td>{E(", ".join(i["flags"]))}</td></tr>' for i in ing['pages_info'])
    topics = ''.join(f'<h3>{E(les["id"])} · {E(les["title"])}</h3><ul>' + ''.join(
        f'<li>{E(t["id"])} {E(t["title"])} <span class="pg">p. {", ".join(map(str, t["pages"]))}</span></li>' for t in les['topics']) + '</ul>'
        for les in o['lessons'])
    made.append(to_pdf(p, 'reference/page_index', 'Topic and page index', f'<h2>Lessons and topics</h2>{topics}<h2>Every page of the PDF</h2>'
                       f'<table><tr><th>Page</th><th>Used in</th><th>Extraction notes</th></tr>{rows}</table>'))
    # formulas and definitions
    fb, db = [], []
    for les in o['lessons']:
        for t in les['topics']:
            for f in t.get('formulas', []):
                fb.append(f'<tr><td><b>{E(f["name"])}</b><div class="f"><span class="tex d">{E(f["latex"])}</span></div></td><td>{E(t["title"])}</td><td>{pg(f)}</td></tr>')
            for d in t.get('definitions', []):
                db.append(f'<tr><td><b>{E(d["term"])}</b></td><td>{rich(d["text"])}</td><td>{pg(d)}</td></tr>')
    ex = []
    for s in p.lesson_specs():
        _, vars_out, _ = calc.apply(load(s), p.meta.get('number_style', 'international'))
        for k, v in vars_out.items():
            if 'page' in v or 'expr' in v:
                ex.append(f'<tr><td class="tex">{E(k)}</td><td>{E(calc.fmt(v["value"], "2" if isinstance(v["value"], float) else ""))} {E(v.get("unit", ""))}</td>'
                          f'<td>{E(v.get("expr", "given"))}</td><td>{"<span class=pg>p. " + str(v["page"]) + "</span>" if "page" in v else "computed"}</td></tr>')
    made.append(to_pdf(p, 'reference/formulas_and_definitions', 'Formulas and definitions',
                       f'<h2>Formulas</h2><table><tr><th>Formula</th><th>Topic</th><th>Source</th></tr>{"".join(fb)}</table>'
                       f'<h2>Definitions</h2><table><tr><th>Term</th><th>Definition</th><th>Source</th></tr>{"".join(db)}</table>'
                       f'<h2>Worked-example values (verified by calculation)</h2><table><tr><th>Symbol</th><th>Value</th><th>How</th><th>Source</th></tr>{"".join(ex)}</table>'))
    # revision notes
    rb = []
    for les in o['lessons']:
        rb.append(f'<h2>{E(les["id"])} · {E(les["title"])}</h2>')
        for t in les['topics']:
            lst = lambda xs: '<ul>' + ''.join(f'<li>{rich(x)}</li>' for x in xs) + '</ul>'  # noqa: E731
            rb.append(f'<h3>{E(t["title"])} <span class="pg">p. {", ".join(map(str, t["pages"]))}</span></h3>'
                      f'<p><b>What:</b> {rich(t["what"])}<br><b>Why:</b> {rich(t["why"])}<br><b>How:</b> {rich(t["how"])}<br>'
                      f'<b>In business:</b> {rich(t["business_use"])}</p>'
                      f'<table><tr><th>Advantages</th><th>Limitations</th></tr><tr><td>{lst(t["advantages"])}</td><td>{lst(t["limitations"])}</td></tr></table>'
                      f'<div class="box"><b>Remember</b>{lst(t["remember"])}</div>'
                      + (f'<p class="supp">Beyond the notes (added explanation, not in the PDF): {E("; ".join(t["supplementary"]))}</p>' if t.get('supplementary') else ''))
    made.append(to_pdf(p, 'revision_notes', 'Revision notes', ''.join(rb)))
    # practice + answer key
    qs = o.get('practice', [])
    made.append(to_pdf(p, 'practice_questions', 'Practice questions', ''.join(
        f'<div class="q"><b>Q{i}.</b> {rich(q["question"])} {pg(q)}</div>' for i, q in enumerate(qs, 1))))
    made.append(to_pdf(p, 'answer_key', 'Answer key', ''.join(
        f'<div class="q"><b>Q{i}.</b> {rich(q["answer"])}' + (f' <span class="tag">checked: {q["_computed"]:.2f}</span>' if '_computed' in q else '') + '</div>'
        for i, q in enumerate(qs, 1))))
    for m in made:
        print('wrote', m)
    return made
