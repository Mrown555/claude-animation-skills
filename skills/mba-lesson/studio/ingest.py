"""PDF ingestion and the page-coverage ledger.

ingest(project): every page -> .build/ingest/pages/pNNN.txt (layout text), pNNN.png (for reading diagrams/formulas),
tables (pdfplumber, when installed) and flags. Writes ingest.json. Nothing is skipped: a page with little text is flagged
"low-text" so it gets read from its image (scanned pages, diagrams).
"""
import re
import subprocess

from common import die, load, run, save

MATH = re.compile(r'[=√∑Σ×÷±≤≥^]|\bsqrt\b|\d\s*[/x×]\s*\d')


def page_count(pdf):
    out = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r'^Pages:\s+(\d+)', out, re.M)
    if not m:
        die(f'pdfinfo could not read {pdf} (is poppler-utils installed?)')
    return int(m.group(1))


def ingest(p, dpi=110):
    pdf = p.root / p.meta['pdf']
    n = page_count(pdf)
    d = p.ingest_dir / 'pages'
    d.mkdir(parents=True, exist_ok=True)
    try:
        import pdfplumber
        plumb = pdfplumber.open(str(pdf))
    except Exception:
        plumb = None
    pages = []
    for i in range(1, n + 1):
        txt = d / f'p{i:03d}.txt'
        run(['pdftotext', '-layout', '-f', i, '-l', i, pdf, txt])
        if not (d / f'p{i:03d}.png').exists():
            run(['pdftoppm', '-f', i, '-l', i, '-r', dpi, '-png', '-singlefile', pdf, d / f'p{i:03d}'])
        text = txt.read_text(encoding='utf-8', errors='replace')
        body = re.sub(r'(?m)^\s*(page\s*)?\d+\s*(/|of)\s*\d+\s*$', '', text, flags=re.I)   # page-number footers
        words = len(body.split())
        info = {'page': i, 'words': words, 'text': f'pages/p{i:03d}.txt', 'image': f'pages/p{i:03d}.png', 'flags': []}
        if words < 25:
            info['flags'].append('low-text: read the page image (scanned page, diagram or title page)')
        if MATH.search(body):
            info['flags'].append('maths')
        if re.search(r'\d', body) and re.search(r'(example|illustration|solution|calculate|find)', body, re.I):
            info['flags'].append('numerical-example')
        if plumb:
            pg = plumb.pages[i - 1]
            tables = [t for t in pg.extract_tables() if t and len(t) > 1]
            if tables:
                info['tables'] = tables
                info['flags'].append(f'{len(tables)} table(s)')
            if pg.images:
                info['flags'].append(f'{len(pg.images)} image(s): check the page image')
        pages.append(info)
    data = {'pdf': p.meta['pdf'], 'pages': n, 'pages_info': pages, 'tables_extracted': plumb is not None}
    save(p.ingest_dir / 'ingest.json', data)
    return data


def numbers_in_source(p):
    """every number printed in the PDF (for the number-traceability check)"""
    out = set()
    for f in sorted((p.ingest_dir / 'pages').glob('p*.txt')):
        for m in re.findall(r'\d[\d,]*\.?\d*', f.read_text(encoding='utf-8', errors='replace')):
            out.add(norm_num(m))
    return out


def norm_num(s):
    s = s.replace(',', '').rstrip('.')
    try:
        v = float(s)
    except ValueError:
        return s
    return f'{v:.6g}'


def coverage(p, outline=None):
    """returns (rows, missing): rows = page -> where it is used; missing = pages not accounted for"""
    ing = load(p.ingest_dir / 'ingest.json')
    o = outline or load(p.outline)
    use = {i: [] for i in range(1, ing['pages'] + 1)}
    for les in o.get('lessons', []):
        for t in les.get('topics', []):
            for pg in t.get('pages', []):
                if pg in use:
                    use[pg].append(f'{les["id"]} · {t["id"]} {t["title"]}')
    for pg, why in (o.get('non_content') or {}).items():
        if int(pg) in use:
            use[int(pg)].append(f'non-content: {why}')
    missing = [i for i, v in use.items() if not v]
    return use, missing
