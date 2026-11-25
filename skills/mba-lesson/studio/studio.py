#!/usr/bin/env python3
"""MBA Animation Studio command line. Run with the kit's venv python:  PY=kit/.venv/bin/python

  studio.py new <pdf> --subject "Operations Management"   create MBA-Studio/<Subject>/<PDF>/ and ingest every page
  studio.py ingest <project>                              (re)extract text, page images, tables, flags
  studio.py coverage <project>                            page ledger: where every page is used
  studio.py check <project>                               validate outline.json (+ every lesson spec)
  studio.py approve <project> --by "<name>"               record the user's outline approval (required before rendering)
  studio.py stills <project> L01 [t1,t2]                  quick JPEG stills of every scene, no video
  studio.py lesson <project> L01 [--lang hinglish]        build one lesson MP4 + SRT
  studio.py complete <project> [--lang hinglish]          join all lessons into the complete MP4 (+ chapters, SRT)
  studio.py qc <project>                                  QC report + contact sheets
  studio.py docs <project>                                narration script, page index, formulas, notes, practice, answers
  studio.py all <project> [--lang hinglish]               every lesson -> complete -> docs -> qc
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Project, die  # noqa: E402


def arg(flag, default=None):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a and a.index(flag) + 1 < len(a) else default


def main():
    a = [x for x in sys.argv[1:]]
    if not a or a[0] in ('-h', '--help'):
        sys.exit(__doc__)
    cmd = a[0]
    lang = arg('--lang', 'en')
    if cmd == 'new':
        import ingest
        subject = arg('--subject') or die('--subject is required')
        p = Project.create(a[1], subject)
        d = ingest.ingest(p)
        print(f'project: {p.root}\npages: {d["pages"]}')
        for pg in d['pages_info']:
            if pg['flags']:
                print(f'  p{pg["page"]}: {", ".join(pg["flags"])}')
        return
    p = Project(a[1] if len(a) > 1 else die('project folder needed'))
    if not p.meta:
        die(f'{p.root} is not a studio project (no project.json)')
    if cmd == 'ingest':
        import ingest
        print(ingest.ingest(p)['pages'], 'pages')
    elif cmd == 'coverage':
        import ingest
        use, missing = ingest.coverage(p)
        for pg, v in use.items():
            print(f'p{pg:>3}: ' + ('; '.join(v) if v else '** NOT ACCOUNTED FOR **'))
        sys.exit(1 if missing else 0)
    elif cmd == 'check':
        import validate
        from common import load
        _, err, warn = validate.outline(p)
        n = load(p.ingest_dir / 'ingest.json')['pages']
        for s in p.lesson_specs():
            e2, w2 = validate.spec(p, load(s), n)
            import calc
            _, _, probs = calc.apply(load(s), p.meta.get('number_style', 'international'))
            err += e2 + [f'{s.stem}: {x}' for x in probs]
            warn += w2
        for w in warn:
            print('warning:', w)
        if err:
            die('\n  ' + '\n  '.join(err))
        print('ok: outline and', len(p.lesson_specs()), 'lesson spec(s) are valid; every page is accounted for')
    elif cmd == 'approve':
        import validate
        err = validate.approve(p, arg('--by') or die('--by "<who approved>" is required'))
        if err:
            die('cannot approve:\n  ' + '\n  '.join(err))
        print('outline approved')
    elif cmd in ('stills', 'lesson'):
        import build
        spec = p.specs / f'{a[2]}.json'
        if not spec.exists():
            die(f'{spec} not found')
        ts = [float(x) for x in a[3].split(',')] if cmd == 'stills' and len(a) > 3 and not a[3].startswith('--') else []
        build.lesson(p, spec, lang, stills=ts if cmd == 'stills' else None)
    elif cmd == 'complete':
        import build
        build.complete(p, lang)
    elif cmd == 'qc':
        import qc
        qc.report(p, lang)
    elif cmd == 'docs':
        import docs
        docs.make(p)
    elif cmd == 'all':
        import build
        import docs
        import qc
        for s in p.lesson_specs():
            build.lesson(p, s, lang)
        build.complete(p, lang)
        docs.make(p)
        qc.report(p, lang)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
