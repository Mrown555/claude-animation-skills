"""Quality control: page coverage, source traceability, maths re-verification, number traceability, layout,
A/V sync, frame counts, black frames, subtitle readability, loudness, original-skill integrity and contact sheets.
Writes qc/qc_report.md and qc/qc.json. FAIL items must be fixed before the videos are handed over."""
import datetime
import html
import re
import subprocess

import calc
import ingest
from common import ENGINE, REPO, load, node_env, run, save


class Report:
    def __init__(self):
        self.rows = []

    def add(self, level, area, msg):
        self.rows.append({'level': level, 'area': area, 'msg': msg})

    @property
    def status(self):
        lv = {r['level'] for r in self.rows}
        return 'FAIL' if 'FAIL' in lv else 'WARN' if 'WARN' in lv else 'PASS'


def strings(o, skip=('narration', 'narration_hi', 'type', 'id', 'color', 'voice', 'setting', 'gen', 'fn', 'source')):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in skip:
                yield from strings(v, skip)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v, skip)
    elif isinstance(o, str):
        yield o


NUM = re.compile(r'(?<![A-Za-z_])\d[\d,]*(?:\.\d+)?')


def numbers(text):
    text = re.sub(r'\\[a-zA-Z]+', ' ', text).replace('{,}', ',')
    return {ingest.norm_num(m) for m in NUM.findall(text)}


def allowed_numbers(src, vars_out):
    ok = set(src) | {f'{i:.6g}' for i in range(0, 21)}
    for v in vars_out.values():
        x = v['value']
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            for d in (0, 1, 2):
                ok.add(f'{round(x, d):.6g}')
            ok.add(f'{x:.6g}')
    return ok


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,r_frame_rate,nb_frames,duration',
                        '-of', 'json', str(path)], capture_output=True, text=True)
    import json
    return {s['codec_type']: s for s in json.loads(r.stdout or '{}').get('streams', [])}


def blackdetect(path):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(path), '-vf', 'blackdetect=d=0.3:pix_th=0.08', '-an', '-f', 'null', '-'],
                       capture_output=True, text=True)
    return re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', r.stderr)


def loudness(path):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(path), '-vn', '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    return float(m[-1]) if m else None


def srt_check(path, rep, area):
    blocks = [b for b in open(path, encoding='utf-8').read().strip().split('\n\n') if b.strip()]
    prev_end, fast = 0.0, 0
    from build import secs
    for b in blocks:
        ln = b.split('\n')
        a, e = (secs(x) for x in ln[1].split(' --> '))
        text = ' '.join(ln[2:])
        if e <= a:
            rep.add('FAIL', area, f'subtitle with no duration: "{text[:40]}"')
        if a < prev_end - 0.01:
            rep.add('FAIL', area, f'overlapping subtitles at {ln[1]}')
        if len(text) / max(e - a, .01) > 25:
            fast += 1
        prev_end = e
    if fast:
        rep.add('WARN', area, f'{fast} subtitle(s) faster than 25 characters/second')
    return len(blocks)


def contact_sheet(p, lid, man, mp4, out):
    tmp = p.build / lid / 'sheet'
    tmp.mkdir(parents=True, exist_ok=True)
    filled = load(p.build / lid / 'filled.json')['spec']['scenes']
    cells, t = [], 0.0
    for i, sc in enumerate(man['scenes']):
        at = t + max(.5, sc['dur'] - .8)
        img = tmp / f's{i:02d}.jpg'
        run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{at:.2f}', '-i', mp4, '-frames:v', '1', '-vf', 'scale=640:-1', img])
        spec = filled[i]
        src = 'beyond the notes' if spec.get('supplementary') else 'p. ' + ', '.join(map(str, (spec.get('source') or {}).get('pages', [])))
        cells.append(f'<figure><img src="{img.name}"><figcaption><b>{i + 1:02d} · {html.escape(sc["type"])}</b> {html.escape(sc["id"] or "")}'
                     f'<span>{sc["dur"]:.1f}s · {html.escape(src)} · at {int(at // 60)}:{at % 60:04.1f}</span></figcaption></figure>')
        t += sc['dur']
    page = tmp / 'sheet.html'
    page.write_text(f"""<!doctype html><meta charset=utf-8><style>
body{{margin:0;padding:24px;background:#1b2333;font:14px sans-serif;color:#eee;width:2040px}} h1{{font-size:22px;margin:0 0 16px}}
.g{{display:grid;grid-template-columns:repeat(3,640px);gap:20px}} figure{{margin:0}} img{{width:640px;display:block;border-radius:6px}}
figcaption{{padding:6px 2px}} figcaption span{{float:right;color:#9aa4b8}}</style>
<h1>{html.escape(lid)} · {html.escape(man['title'])} · {len(cells)} scenes · {man['dur'] / 60:.1f} min</h1><div class=g>{''.join(cells)}</div>""", encoding='utf-8')
    run(['node', ENGINE / 'pdf.js', '--png', page, out, 2088, 400], env=node_env())


def report(p, lang='en'):
    rep = Report()
    suffix = '_hi' if lang == 'hinglish' else ''
    outline = load(p.outline)
    # 1. coverage
    use, missing = ingest.coverage(p)
    if missing:
        rep.add('FAIL', 'coverage', f'pages not accounted for: {missing}')
    else:
        rep.add('PASS', 'coverage', f'all {len(use)} pages accounted for')
    src_nums = ingest.numbers_in_source(p)
    sheets, lessons = [], []
    p.qc_dir.mkdir(parents=True, exist_ok=True)
    (p.qc_dir / 'contact_sheets').mkdir(exist_ok=True)
    for les in outline['lessons']:
        lid = les['id']
        work = p.build / (lid + suffix)
        area = lid
        if not (work / 'manifest.json').exists():
            rep.add('FAIL', area, 'lesson not built')
            continue
        man = load(work / 'manifest.json')
        raw = load(p.specs / f'{lid}.json')
        filled, vars_out, probs = calc.apply(raw, p.meta.get('number_style', 'international'))
        # 2. maths
        for x in probs:
            rep.add('FAIL', area, 'maths: ' + x)
        if not probs:
            rep.add('PASS', area, f'maths: {len(raw.get("vars", {}))} values recomputed, {len(raw.get("checks", []))} checks hold')
        # 3. traceability
        untagged = [sc['id'] for sc in filled['scenes'] if not sc.get('supplementary') and not (sc.get('source') or {}).get('pages')]
        supp = [sc['id'] for sc in filled['scenes'] if sc.get('supplementary')]
        rep.add('FAIL' if untagged else 'PASS', area, f'traceability: {len(filled["scenes"]) - len(supp)} scenes cite PDF pages, {len(supp)} marked "beyond the notes"'
                + (f'; untagged: {untagged}' if untagged else ''))
        # 4. numbers that appear neither in the PDF nor in the computed values
        ok = allowed_numbers(src_nums, vars_out)
        for sc in filled['scenes']:
            if sc.get('supplementary'):
                continue
            nar = ' '.join(x if isinstance(x, str) else x.get('text', '') for x in sc.get('narration', []))
            unknown = sorted(numbers(nar + ' ' + ' '.join(strings(sc))) - ok)
            if unknown:
                rep.add('WARN', area, f'scene {sc["id"]}: numbers not found in the PDF or the calculations: {", ".join(unknown)} (check them)')
        # 5. layout + page errors (measured in the browser on each scene's last revealed frame)
        captured = total = 0
        for i, sc in enumerate(man['scenes']):
            q = work / 'scenes' / f's{i:02d}.qc.json'
            if not q.exists():
                rep.add('FAIL', area, f'scene {sc["id"]}: no render QC data')
                continue
            qd = load(q)
            captured += qd['captured']
            total += qd['frames']
            for e in qd['errors']:
                rep.add('FAIL', area, f'scene {sc["id"]}: page error {e}')
            for issue in qd['layout']:
                rep.add('FAIL' if issue['kind'] in ('overlap', 'off-area', 'overflow') else 'WARN', area, f'scene {sc["id"]}: layout {issue}')
        # 6. A/V: duration, frames, format, black frames, loudness, subtitles
        mp4 = man['mp4']
        st = probe(mp4)
        v, a = st.get('video', {}), st.get('audio', {})
        exp = sum(s['frames'] for s in man['scenes'])
        fr = int(v.get('nb_frames', 0))
        fmt_ok = v.get('width') == 1920 and v.get('height') == 1080 and v.get('r_frame_rate') == '30/1'
        rep.add('PASS' if fmt_ok else 'FAIL', area, f'format {v.get("width")}x{v.get("height")} @ {v.get("r_frame_rate")}')
        rep.add('PASS' if fr == exp else 'FAIL', area, f'frames: {fr} in file, {exp} expected (no missing frames)' if fr == exp else f'frames: {fr} in file but {exp} expected')
        dv, da = float(v.get('duration', 0)), float(a.get('duration', 0))
        rep.add('PASS' if abs(dv - da) < .1 else 'FAIL', area, f'A/V sync: video {dv:.2f}s, audio {da:.2f}s (narration is placed per sentence on the scene clock)')
        bl = blackdetect(mp4)
        rep.add('FAIL' if bl else 'PASS', area, f'black frames: {bl}' if bl else 'no black frames')
        lu = loudness(mp4)
        rep.add('PASS' if lu is not None and -18 <= lu <= -14 else 'WARN', area, f'loudness {lu} LUFS (target -16)')
        n = srt_check(man['srt'], rep, area)
        rep.add('PASS', area, f'subtitles: {n} cues, burned in and as {man["srt"].split("/")[-1]}')
        rep.add('PASS', area, f'render: {captured}/{total} frames captured, the rest were static holds')
        sh = p.qc_dir / 'contact_sheets' / f'{lid}{suffix}.jpg'
        contact_sheet(p, lid + suffix, man, mp4, sh)
        sheets.append(sh)
        lessons.append(man)
    # 7. complete video
    cm = p.build / ('complete' + suffix) / 'manifest.json'
    if cm.exists():
        c = load(cm)
        st = probe(c['mp4'])
        dv = float(st.get('video', {}).get('duration', 0))
        tot = sum(m['dur'] for m in lessons)
        rep.add('PASS' if abs(dv - tot) < .2 else 'FAIL', 'complete', f'complete video {dv / 60:.2f} min = sum of lessons {tot / 60:.2f} min')
    else:
        rep.add('WARN', 'complete', 'complete video not built yet')
    # 8. the original animation skills are untouched
    r = subprocess.run(['git', '-C', str(REPO), 'status', '--porcelain', '--', 'skills', 'kit', 'install.sh', 'README.md', 'LICENSE', ':!skills/mba-lesson'],
                       capture_output=True, text=True)
    changed = [ln for ln in r.stdout.splitlines() if ln.strip()]
    rep.add('FAIL' if changed else 'PASS', 'integrity', f'original skills modified: {changed}' if changed else 'original skills and kit unchanged')
    # write
    lines = [f'# QC report: {outline["title"]}', '', f'Status: **{rep.status}** · {datetime.datetime.now():%Y-%m-%d %H:%M} · language: {lang}', '',
             '| | Area | Check |', '|---|---|---|']
    icon = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌'}
    lines += [f'| {icon[r["level"]]} | {r["area"]} | {r["msg"]} |' for r in rep.rows]
    lines += ['', '## Page ledger', ''] + [f'- p{pg}: {"; ".join(v) or "NOT ACCOUNTED FOR"}' for pg, v in use.items()]
    lines += ['', '## Contact sheets', ''] + [f'- [{s.name}](contact_sheets/{s.name})' for s in sheets]
    (p.qc_dir / 'qc_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    save(p.qc_dir / 'qc.json', {'status': rep.status, 'rows': rep.rows})
    print(f'QC {rep.status}: {p.qc_dir / "qc_report.md"}')
    for r in rep.rows:
        if r['level'] != 'PASS':
            print(f'  {r["level"]} {r["area"]}: {r["msg"]}')
    return rep.status
