"""Lesson build: spec -> verified maths -> narration + timing -> parallel scene render -> lesson MP4 (+SRT) -> complete MP4."""
import json
import subprocess
import sys

import numpy as np
import soundfile as sf

import calc
import validate
import voice
from common import ENGINE, MAX_WORKERS, die, digest, load, node_env, run, save, slug

SRT_T = lambda s: f'{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(round(s % 1 * 1000)) % 1000:03d}'  # noqa: E731


SCENE_FILE = {'title': 'basic', 'concept': 'basic', 'bullets': 'basic', 'table': 'basic', 'formula': 'formula', 'calc': 'formula',
              'chart': 'chart', 'process': 'diagram', 'matrix': 'diagram', 'roleplay': 'roleplay'}


def engine_hash(kind):
    """cache key part: the engine core plus only the module that draws this scene type"""
    files = [ENGINE / 'engine.js', ENGINE / 'theme.css', ENGINE / 'index.html', ENGINE / 'render.js', ENGINE / 'scenes' / f'{SCENE_FILE.get(kind, kind)}.js']
    return digest([f.read_text() for f in files if f.exists()])


def prepare(p, spec_path, lang):
    raw = load(spec_path)
    n_pages = load(p.ingest_dir / 'ingest.json')['pages']
    err, warn = validate.spec(p, raw, n_pages)
    if lang == 'hinglish':
        for sc in raw['scenes']:
            if len(sc.get('narration_hi') or []) != len(sc['narration']):
                err.append(f'{raw["id"]}/{sc["id"]}: Hinglish needs narration_hi with the same number of sentences as narration')
    filled, vars_out, problems = calc.apply(raw, p.meta.get('number_style', 'international'))
    err += problems
    if err:
        die('lesson spec problems:\n  ' + '\n  '.join(err))
    for w in warn:
        print('warning:', w)
    return raw, filled, vars_out


def render_scenes(p, lid, data, work):
    todo = []
    for i, sc in enumerate(data['scenes']):
        h = digest([sc, engine_hash(sc['spec']['type']), data['theme'], data['lesson']])
        tag = work / 'scenes' / f's{i:02d}'
        if (tag.with_suffix('.mp4')).exists() and (tag.with_suffix('.hash')).exists() and tag.with_suffix('.hash').read_text() == h:
            continue
        todo.append((i, h, sc['timing']['frames'] * (3 if sc['spec']['type'] == 'roleplay' else 1)))
    if not todo:
        print(f'{lid}: all scenes up to date')
        return
    nw = max(1, min(MAX_WORKERS, len(todo)))
    groups = [[] for _ in range(nw)]
    load_ = [0] * nw
    for i, h, cost in sorted(todo, key=lambda x: -x[2]):
        k = load_.index(min(load_))
        groups[k].append(i)
        load_[k] += cost
    print(f'{lid}: rendering {len(todo)} scene(s) with {nw} worker(s)', flush=True)
    env = node_env()
    procs = [subprocess.Popen(['node', str(ENGINE / 'render.js'), str(work), ','.join(map(str, g))], env=env) for g in groups if g]
    codes = [pr.wait() for pr in procs]
    if any(codes):
        die(f'{lid}: a render worker failed (see output above)')
    for i, h, _ in todo:
        (work / 'scenes' / f's{i:02d}.hash').write_text(h)


def lesson(p, spec_path, lang='en', stills=None):
    ok, info = validate.approved(p)
    if not ok:
        die(info)
    raw, filled, vars_out = prepare(p, spec_path, lang)
    lid = filled['id']
    work = p.work(lid + ('_hi' if lang == 'hinglish' else ''))
    (work / 'audio').mkdir(parents=True, exist_ok=True)
    cache = p.build / 'tts_cache'
    scenes, audio = [], []
    for sc in filled['scenes']:
        timing, a = voice.scene_audio(sc, p.meta, cache, lang)
        scenes.append({'spec': {k: v for k, v in sc.items() if k not in ('narration', 'narration_hi')}, 'timing': timing})
        audio.append(a)
    outline = load(p.outline)
    order = [les['id'] for les in outline['lessons']]
    data = {'lesson': {'id': lid, 'title': filled['title'], 'index': order.index(lid) + 1 if lid in order else 1, 'total': len(order)},
            'theme': p.meta.get('theme', {}), 'style': p.meta.get('style', 'clean'), 'scenes': scenes}
    (work / 'lesson-data.js').write_text('window.LESSON = ' + json.dumps(data, ensure_ascii=False) + ';\n', encoding='utf-8')
    save(work / 'filled.json', {'spec': filled, 'vars': vars_out})
    if stills is not None:
        env = node_env()
        for i, sc in enumerate(scenes):
            d = sc['timing']['dur']
            ts = stills or [round(d * .5, 1), round(d - .7, 1)]
            run(['node', ENGINE / 'render.js', work, i, '--stills', ','.join(map(str, ts))], env=env)
        print('stills in', work / 'scenes')
        return
    render_scenes(p, lid, data, work)
    # audio: scene by scene, exactly as long as the video, then a ducked music bed under the whole lesson
    mix = np.concatenate(audio) if audio else np.zeros(0, np.float32)
    if p.meta.get('music', True):
        mix = mix + voice.music_bed(len(mix), mix)
    voice.write(str(work / 'audio' / 'mix.wav'), mix)
    lst = work / 'concat.txt'
    lst.write_text(''.join(f"file '{work / 'scenes' / f's{i:02d}.mp4'}'\n" for i in range(len(scenes))))
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', work / 'silent.mp4'])
    out_dir = p.lessons_dir if lang == 'en' else p.root / 'lessons_hinglish'
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f'{lid}_{slug(filled["title"])}'
    mp4 = out_dir / f'{name}.mp4'
    mux(work / 'silent.mp4', work / 'audio' / 'mix.wav', mp4)
    t, srt, n = 0.0, [], 1
    for sc in scenes:
        for s in sc['timing']['subs']:
            srt.append(f'{n}\n{SRT_T(t + s["s"])} --> {SRT_T(t + s["e"])}\n{s["text"]}\n')
            n += 1
        t += sc['timing']['dur']
    mp4.with_suffix('.srt').write_text('\n'.join(srt), encoding='utf-8')
    save(work / 'manifest.json', {'id': lid, 'title': filled['title'], 'mp4': str(mp4), 'dur': t, 'scenes': [
        {'id': sc['spec'].get('id'), 'type': sc['spec']['type'], 'dur': sc['timing']['dur'], 'frames': sc['timing']['frames']} for sc in scenes],
        'silent': str(work / 'silent.mp4'), 'mix': str(work / 'audio' / 'mix.wav'), 'srt': str(mp4.with_suffix('.srt')), 'lang': lang})
    print(f'done: {mp4}  ({t / 60:.1f} min)')
    return work / 'manifest.json'


def mux(video, wav, out, meta=None):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', video, '-i', wav]
    if meta:
        cmd += ['-i', meta, '-map_metadata', '2', '-map_chapters', '2']
    cmd += ['-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k',
            '-ar', '48000', '-shortest', '-movflags', '+faststart', out]
    run(cmd)


def complete(p, lang='en'):
    outline = load(p.outline)
    mans = []
    for les in outline['lessons']:
        f = p.work(les['id'] + ('_hi' if lang == 'hinglish' else '')) / 'manifest.json'
        if not f.exists():
            die(f'lesson {les["id"]} has not been built yet')
        mans.append(load(f))
    work = p.build / ('complete_hi' if lang == 'hinglish' else 'complete')
    work.mkdir(parents=True, exist_ok=True)
    (work / 'concat.txt').write_text(''.join(f"file '{m['silent']}'\n" for m in mans))
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', work / 'concat.txt', '-c', 'copy', work / 'silent.mp4'])
    wav = np.concatenate([sf.read(m['mix'], dtype='float32')[0] for m in mans])
    voice.write(str(work / 'mix.wav'), wav)
    meta, t = [';FFMETADATA1', f'title={outline["title"]}'], 0.0
    srt, n = [], 1
    for m in mans:
        meta += ['[CHAPTER]', 'TIMEBASE=1/1000', f'START={int(t * 1000)}', f'END={int((t + m["dur"]) * 1000)}', f'title={m["id"]} {m["title"]}']
        for block in open(m['srt'], encoding='utf-8').read().strip().split('\n\n'):
            ln = block.split('\n')
            if len(ln) < 3:
                continue
            a, b = ln[1].split(' --> ')
            srt.append(f'{n}\n{SRT_T(t + secs(a))} --> {SRT_T(t + secs(b))}\n' + '\n'.join(ln[2:]) + '\n')
            n += 1
        t += m['dur']
    (work / 'chapters.txt').write_text('\n'.join(meta) + '\n', encoding='utf-8')
    out = p.root / f'00_{slug(p.meta["title"])}_complete{"_hinglish" if lang == "hinglish" else ""}.mp4'
    mux(work / 'silent.mp4', work / 'mix.wav', out, work / 'chapters.txt')
    out.with_suffix('.srt').write_text('\n'.join(srt), encoding='utf-8')
    save(work / 'manifest.json', {'mp4': str(out), 'dur': t, 'lessons': [m['id'] for m in mans]})
    print(f'done: {out}  ({t / 60:.1f} min)')


def secs(s):
    h, m, rest = s.split(':')
    sec, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


if __name__ == '__main__':
    sys.exit('use studio.py')
