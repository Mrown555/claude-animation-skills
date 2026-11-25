"""Narration (Kokoro, local), scene timing, subtitles and the sound bed. Run with kit/.venv/bin/python.

Each narration sentence is synthesised on its own and cached, so a scene's timing is known exactly at sentence level
(this also works for Hindi/Hinglish, where word alignment is not available). Subtitle chunks inside a sentence are
timed in proportion to their length.
SFX functions are ported from the stick-figure skill's audio.py (MIT, Artem Novitckii).
"""
import hashlib
import os
import re

import numpy as np
import soundfile as sf
from scipy import signal

from common import FPS, KIT

SR = 24000
LEAD, GAP, TAIL = .75, .45, 1.2
_kokoro = None


def kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        m = KIT / 'models'
        if not (m / 'kokoro-v1.0.onnx').exists():
            raise SystemExit(f'Kokoro voice model missing: run  bash {KIT}/setup.sh --voice')
        _kokoro = Kokoro(str(m / 'kokoro-v1.0.onnx'), str(m / 'voices-v1.0.bin'))
    return _kokoro


KEEP_CAPS = {'I', 'A', 'OK', 'CEO', 'GDP'}


def speakable(text, say=None):
    """what the voice reads: rupee amounts, symbols and acronyms spelled out"""
    if say:
        return say
    t = re.sub(r'\*\*', '', text)
    t = re.sub(r'(?:₹|Rs\.?\s?|INR\s?)(\d[\d,]*(?:\.\d+)?)', r'\1 rupees', t)
    t = t.replace('×', ' times ').replace('÷', ' divided by ').replace('≈', ' approximately ').replace('√', ' square root of ')
    t = re.sub(r'(\d)\s*%', r'\1 percent', t)
    t = re.sub(r'(?<=[a-zA-Z0-9])/(?=[a-zA-Z])', ' per ', t)
    t = re.sub(r'\b([A-Z]{2,5})s?\b', lambda m: m.group(0) if m.group(1) in KEEP_CAPS else ' '.join(m.group(1)) + ('s' if m.group(0).endswith('s') and not m.group(1).endswith('S') else ''), t)
    return re.sub(r'\s+', ' ', t).strip()


def subtitle_text(text):
    t = re.sub(r'\*\*', '', text)
    return re.sub(r'\$([^$]+)\$', lambda m: re.sub(r'[\\{}]', '', m.group(1)), t)


def tts(text, voice, speed, lang, cache):
    key = hashlib.sha256(f'{voice}|{speed}|{lang}|{text}'.encode()).hexdigest()[:20]
    f = cache / f'{key}.wav'
    if f.exists():
        a, _ = sf.read(f, dtype='float32')
        return a
    a, sr = kokoro().create(text, voice=voice, speed=speed, lang=lang)
    assert sr == SR, sr
    idx = np.where(np.abs(a) > .01)[0]
    if len(idx):
        a = a[max(0, idx[0] - int(.02 * SR)): idx[-1] + int(.08 * SR)]
    cache.mkdir(parents=True, exist_ok=True)
    sf.write(f, a, SR)
    return a.astype(np.float32)


def chunks(text, maxc=88):
    words, out, cur = text.split(), [], ''
    for w in words:
        if cur and len(cur) + 1 + len(w) > maxc:
            out.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
        if cur.endswith((',', ';', ':')) and len(cur) > maxc * .55:
            out.append(cur)
            cur = ''
    if cur:
        out.append(cur)
    return out


# ---------------- SFX (ported from skills/stick-figure/engine/template/audio.py) ----------------
rng = np.random.default_rng(3)
T = lambda n: np.arange(n) / SR  # noqa: E731


def bp(x, lo, hi):
    b, a = signal.butter(2, [lo / (SR / 2), min(hi / (SR / 2), .99)], 'band')
    return signal.lfilter(b, a, x)


def lp(x, f):
    b, a = signal.butter(2, f / (SR / 2), 'low')
    return signal.lfilter(b, a, x)


def whoosh(dur=.4):
    n = int(dur * SR); x = rng.standard_normal(n); t = T(n); k = np.linspace(0, 1, n)
    return (bp(x, 250, 1200) * (1 - k) + bp(x, 1500, 6000) * k) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 * 1.2


def pop(f=620):
    n = int(.12 * SR); t = T(n); fr = f * (1 + 2 * t * 10)
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 40)


def tick():
    n = int(.05 * SR); t = T(n)
    return np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 120) * .6


def chime(f=1318, dur=1.0):
    n = int(dur * SR); t = T(n)
    return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.01 * t) + .3 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t * 4) * np.minimum(1, t / .004) * .45


SFX = {'whoosh': (whoosh, .10), 'pop': (pop, .10), 'tick': (tick, .12), 'chime': (chime, .16)}


def place(buf, x, at, g):
    i = int(at * SR); j = min(len(buf), i + len(x))
    if 0 <= i < len(buf):
        buf[i:j] += x[:j - i] * g


def scene_cues(sc, sent):
    """SFX cue times for items that carry an explicit 'at' (mirrors ctx.cue in engine.js)"""
    cues = [('whoosh', .02)]
    kind = {'calc': 'tick', 'formula': 'tick'}.get(sc['type'], 'pop')

    def walk(o, key=None):
        if isinstance(o, dict):
            if isinstance(o.get('at'), (int, float)) and sent:
                i = max(0, min(len(sent) - 1, round(o['at'])))
                t = sent[i]['s'] + (o.get('delay') if o.get('delay') is not None else (.6 if o['at'] == 0 else .1))
                cues.append(('chime' if key == 'result' else kind, t))
            for k, v in o.items():
                walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
    walk({k: v for k, v in sc.items() if k != 'narration'})
    return cues


def scene_audio(sc, meta, cache, lang):
    """returns (timing, mono float32 audio at SR) for one scene"""
    hin = lang == 'hinglish'
    lines = sc.get('narration_hi') if hin else sc['narration']
    voice = meta.get('hinglish_voice', 'hf_alpha') if hin else meta.get('voice', 'am_michael')
    klang = meta.get('hinglish_lang', 'hi') if hin else 'en-us'
    parts, sent, subs, t = [], [], [], LEAD
    for ln in lines:
        item = ln if isinstance(ln, dict) else {'text': ln}
        a = tts(speakable(item['text'], item.get('say')), item.get('voice', voice), float(meta.get('speed', 1.0)), klang, cache)
        d = len(a) / SR
        sent.append({'s': round(t, 3), 'e': round(t + d, 3)})
        parts.append((t, a))
        cs = chunks(subtitle_text(item['text']))
        total = sum(len(c) for c in cs) or 1
        cur = t
        for c in cs:
            dd = d * len(c) / total
            subs.append({'s': round(cur, 3), 'e': round(cur + dd + (.25 if c is cs[-1] else 0), 3), 'text': c})
            cur += dd
        t += d + GAP + float(item.get('pause', 0))
    dur = t - GAP + TAIL + float(sc.get('hold', 0))
    frames = int(np.ceil(dur * FPS))
    dur = frames / FPS
    buf = np.zeros(int(round(dur * SR)), dtype=np.float64)
    for st, a in parts:
        place(buf, a, st, 1.0)
    if meta.get('sfx', True):
        for name, at in scene_cues(sc, sent):
            fn, g = SFX[name]
            place(buf, fn(), at, g)
    for s in subs:
        s['e'] = min(s['e'], dur - .3)
    return {'dur': dur, 'frames': frames, 'sent': sent, 'subs': subs}, buf.astype(np.float32)


def music_bed(n, voice):
    """a quiet two-chord pad, ducked under the voice (sidechain from the narration envelope)"""
    if n == 0:
        return np.zeros(0, np.float32)
    t = np.arange(n) / SR
    chords = [[220.0, 277.18, 329.63], [196.0, 246.94, 293.66]]
    seg = (t // 8).astype(int) % 2
    x = np.zeros(n)
    for k in range(3):
        f = np.where(seg == 0, chords[0][k], chords[1][k])
        x += np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 + .3 * np.sin(2 * np.pi * .07 * t + k))
    x = lp(x, 900) / 3
    env = np.abs(voice)
    win = int(.25 * SR)
    env = np.convolve(env, np.ones(win) / win, 'same')
    duck = 1 - .65 * np.clip(env / (env.max() * .3 + 1e-9), 0, 1)
    fade = np.minimum(1, np.minimum(t / 2, (t[-1] - t) / 2 + 1e-9))
    return (x * duck * fade * .035).astype(np.float32)


def write(path, a):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, a, SR)
