"""Shared paths and helpers for the MBA Animation Studio. Standard library only."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
SKILL = STUDIO.parent
ENGINE = SKILL / 'engine16x9'
REPO = SKILL.parents[1]
KIT = REPO / 'kit'
VENV_PY = KIT / '.venv' / 'bin' / 'python'
FPS, W, H = 30, 1920, 1080
HOME = Path(os.environ.get('MBA_STUDIO_HOME', Path.home() / 'MBA-Studio'))
MAX_WORKERS = int(os.environ.get('STUDIO_WORKERS', '4'))


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def save(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def slug(s, n=48):
    s = re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')
    return s[:n] or 'untitled'


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def ffprobe(path, entry='format=duration'):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', entry, '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return r.stdout.strip()


def count_frames(path):
    out = ffprobe(path, 'stream=nb_frames')
    return int(out.split()[0]) if out and out.split()[0].isdigit() else None


def node_env():
    env = dict(os.environ)
    paths = []
    if (KIT / 'node_modules' / 'playwright').exists():
        paths.append(str(KIT / 'node_modules'))
    g = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()
    if g:
        paths.append(g)
    env['NODE_PATH'] = os.pathsep.join(paths + [env.get('NODE_PATH', '')]).strip(os.pathsep)
    return env


def die(msg):
    sys.exit('error: ' + msg)


class Project:
    """MBA-Studio/<Subject>/<PDF name>/ : everything for one PDF."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.meta = load(self.root / 'project.json') if (self.root / 'project.json').exists() else {}

    build = property(lambda s: s.root / '.build')
    ingest_dir = property(lambda s: s.root / '.build' / 'ingest')
    outline = property(lambda s: s.root / 'outline.json')
    specs = property(lambda s: s.root / 'specs')
    lessons_dir = property(lambda s: s.root / 'lessons')
    qc_dir = property(lambda s: s.root / 'qc')

    def lesson_specs(self):
        return sorted(self.specs.glob('L*.json'))

    def work(self, lid):
        return self.build / lid

    @staticmethod
    def create(pdf, subject):
        pdf = Path(pdf).resolve()
        if not pdf.exists():
            die(f'{pdf} not found')
        root = HOME / slug(subject, 60) / slug(pdf.stem, 60)
        (root / 'source').mkdir(parents=True, exist_ok=True)
        dst = root / 'source' / pdf.name
        if not dst.exists():
            shutil.copy2(pdf, dst)
        p = Project(root)
        if not p.meta:
            p.meta = {'subject': subject, 'pdf': f'source/{pdf.name}', 'title': pdf.stem, 'language': 'en',
                      'voice': 'am_michael', 'speed': 1.0, 'hinglish_voice': 'hf_alpha', 'number_style': 'international', 'music': True}
            save(root / 'project.json', p.meta)
        return p
