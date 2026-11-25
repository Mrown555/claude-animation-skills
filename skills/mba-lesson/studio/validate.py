"""Schema checks for outline.json and lesson specs, and the outline approval gate."""
import datetime

from common import digest, load, save
from ingest import coverage

TOPIC_KEYS = ['id', 'title', 'pages', 'what', 'why', 'how', 'business_use', 'advantages', 'limitations', 'remember']
SCENES = {'title', 'concept', 'bullets', 'table', 'formula', 'calc', 'chart', 'process', 'matrix', 'roleplay'}
LIMITS = {'bullets': ('items', 6), 'process': ('steps', 5), 'table': ('rows', 7), 'calc': ('steps', 6), 'matrix': ('cells', 4), 'concept': ('points', 4)}


def outline(p):
    o = load(p.outline)
    err, warn = [], []
    n_pages = load(p.ingest_dir / 'ingest.json')['pages']
    for k in ('subject', 'title', 'lessons'):
        if not o.get(k):
            err.append(f'outline: missing "{k}"')
    ids = set()
    for les in o.get('lessons', []):
        if not les.get('id') or not les.get('title') or not les.get('topics'):
            err.append(f'lesson {les.get("id")}: needs id, title and topics')
        for t in les.get('topics', []):
            for k in TOPIC_KEYS:
                if not t.get(k):
                    err.append(f'{les.get("id")}/{t.get("id")}: missing "{k}"')
            ids.add(t.get('id'))
            for pg in t.get('pages', []):
                if not isinstance(pg, int) or not 1 <= pg <= n_pages:
                    err.append(f'{t.get("id")}: page {pg} does not exist')
            for f in t.get('formulas', []):
                if not f.get('latex') or not f.get('page'):
                    err.append(f'{t.get("id")}: every formula needs latex and page')
            for d in t.get('definitions', []):
                if not d.get('term') or not d.get('text') or not (d.get('page') or d.get('supplementary')):
                    err.append(f'{t.get("id")}: every definition needs term, text and page (or supplementary)')
    for q in o.get('practice', []):
        if not q.get('question') or not q.get('answer'):
            err.append('practice: every question needs question and answer')
        if not (q.get('page') or q.get('supplementary')):
            err.append(f'practice "{q.get("question", "")[:40]}": needs page or supplementary: true')
    _, missing = coverage(p, o)
    if missing:
        err.append(f'pages not accounted for: {missing} (add them to a topic or to "non_content" with a reason)')
    return o, err, warn


def approve(p, by):
    o, err, _ = outline(p)
    if err:
        return err
    save(p.root / 'outline.approval.json', {'hash': digest(o), 'approved_by': by, 'at': datetime.datetime.now().isoformat(timespec='seconds')})
    return []


def approved(p):
    f = p.root / 'outline.approval.json'
    if not f.exists():
        return False, 'the outline has not been approved yet (show it to the user, then run: studio.py approve)'
    a = load(f)
    if a['hash'] != digest(load(p.outline)):
        return False, 'outline.json changed after approval: show the changes to the user and approve again'
    return True, a


def spec(p, s, n_pages):
    err, warn = [], []
    topics = {t['id'] for les in load(p.outline)['lessons'] for t in les['topics']}
    for t in s.get('topics', []):
        if t not in topics:
            err.append(f'{s.get("id")}: topic {t} is not in the outline')
    for sc in s.get('scenes', []):
        sid = f'{s.get("id")}/{sc.get("id")}'
        if sc.get('type') not in SCENES:
            err.append(f'{sid}: unknown type {sc.get("type")}')
        nar = sc.get('narration') or []
        if not nar:
            err.append(f'{sid}: no narration')
        src = (sc.get('source') or {}).get('pages')
        if not src and not sc.get('supplementary'):
            err.append(f'{sid}: needs source.pages or supplementary: true (traceability)')
        for pg in src or []:
            if not 1 <= pg <= n_pages:
                err.append(f'{sid}: source page {pg} does not exist')
        for line in nar:
            text = line if isinstance(line, str) else line.get('text', '')
            if len(text.split()) > 38:
                warn.append(f'{sid}: long sentence ({len(text.split())} words), split it for clearer narration')
            if '$' in text or '\\' in text:
                err.append(f'{sid}: narration contains TeX; write maths as spoken words')
        lim = LIMITS.get(sc.get('type'))
        if lim and len(sc.get(lim[0], [])) > lim[1]:
            err.append(f'{sid}: {len(sc[lim[0]])} {lim[0]} (max {lim[1]}); split the scene')

        def walk(o):
            if isinstance(o, dict):
                if 'at' in o and isinstance(o['at'], (int, float)) and o['at'] >= len(nar):
                    err.append(f'{sid}: cue at={o["at"]} but the scene has {len(nar)} sentences')
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk({k: v for k, v in sc.items() if k != 'narration'})
    return err, warn
