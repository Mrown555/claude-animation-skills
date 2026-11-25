"""Exact, auditable maths for lesson specs.

A lesson spec declares "vars": {"D": {"value": 12000, "page": 3}, "EOQ": {"expr": "sqrt(2*D*S/H)"}}.
Every {{name}} or {{name|fmt}} in the spec's text (narration, on-screen TeX, notes) is replaced by the computed value,
so narration and visuals cannot disagree. "checks" are assertions that must hold. Chart series with "fn" are sampled here.
Formats: {{X}} auto, {{X|0}} / {{X|2}} decimals, {{X|in}} Indian grouping (1,20,000), {{X|raw}} no grouping, {{X|%}} percent.
"""
import ast
import math
import re

FUNCS = {'sqrt': math.sqrt, 'ceil': math.ceil, 'floor': math.floor, 'round': round, 'min': min, 'max': max, 'abs': abs,
         'log': math.log, 'ln': math.log, 'exp': math.exp, 'log10': math.log10}
OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
       ast.Pow: lambda a, b: a ** b, ast.Mod: lambda a, b: a % b, ast.FloorDiv: lambda a, b: a // b}
CMP = {ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
       ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b}


class CalcError(Exception):
    pass


def ev(expr, env):
    """safe evaluator: numbers, variables, + - * / ** %, comparisons, and/or, and the FUNCS above"""
    def go(n):
        if isinstance(n, ast.Expression):
            return go(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in env:
                return env[n.id]
            if n.id == 'pi':
                return math.pi
            raise CalcError(f'unknown variable "{n.id}" in {expr!r}')
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            return OPS[type(n.op)](go(n.left), go(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = go(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.Compare):
            left = go(n.left)
            for op, c in zip(n.ops, n.comparators):
                right = go(c)
                if not CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.BoolOp):
            vals = [go(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS:
            return FUNCS[n.func.id](*[go(a) for a in n.args])
        raise CalcError(f'unsupported expression {expr!r}')
    try:
        return go(ast.parse(str(expr), mode='eval'))
    except ZeroDivisionError:
        raise CalcError(f'division by zero in {expr!r}')
    except SyntaxError:
        raise CalcError(f'cannot parse {expr!r}')


def solve(vars_spec):
    env, out = {}, {}
    for name, v in vars_spec.items():
        if 'value' in v:
            val = v['value']
        elif 'expr' in v:
            val = ev(v['expr'], env)
        else:
            raise CalcError(f'var {name} needs "value" or "expr"')
        if v.get('round') is not None:
            val = round(val, v['round']) if v['round'] > 0 else int(round(val))
        if v.get('ceil'):
            val = math.ceil(val)
        env[name] = val
        out[name] = {'value': val, **{k: v[k] for k in ('expr', 'page', 'unit', 'note') if k in v}}
    return env, out


def group(intpart, style):
    s = str(intpart)
    if style == 'in' and len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r'(\d)(?=(\d\d)+$)', r'\1,', head)
        return head + ',' + tail
    return f'{intpart:,}' if style != 'raw' else s


def fmt(v, f='', style='international'):
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if f == '%':
        return fmt(v * 100, '', style) + '%'
    dec = int(f) if f.isdigit() else None
    if f in ('in', 'raw'):
        style, dec = f, None
    if dec is None:
        dec = 0 if abs(v - round(v)) < 1e-9 else (2 if abs(v) < 1e6 else 0)
    neg = v < 0
    v = abs(v)
    s = f'{v:.{dec}f}'
    ip, _, fp = s.partition('.')
    g = group(int(ip), 'in' if style in ('in', 'indian') else style)
    if fp:
        fp = fp.rstrip('0') if not f.isdigit() else fp
    return ('-' if neg else '') + g + ('.' + fp if fp else '')


PH = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\|\s*([^}]*?))?\s*\}\}')
TEX_KEYS = {'tex', 'latex', 'sym'}


def fill(obj, env, style, key=None, missing=None):
    """replace {{var}} everywhere; inside TeX, digit-group commas become {,} so KaTeX does not add a space"""
    if isinstance(obj, dict):
        return {k: fill(v, env, style, k, missing) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fill(v, env, style, key, missing) for v in obj]
    if not isinstance(obj, str):
        return obj

    def rep(m):
        if m.group(1) not in env:
            if missing is not None:
                missing.add(m.group(1))
            return m.group(0)
        return fmt(env[m.group(1)], (m.group(2) or '').strip(), style)
    s = PH.sub(rep, obj)
    if key in TEX_KEYS:
        s = re.sub(r'(?<=\d),(?=\d{2,3}\b)', '{,}', s)
    else:
        s = re.sub(r'\$[^$]+\$', lambda m: re.sub(r'(?<=\d),(?=\d{2,3}\b)', '{,}', m.group(0)), s)
    return s


def sample(fn, env, x0, x1, n=80):
    pts = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        if x == 0:
            x = (x1 - x0) * 1e-3 if x1 > x0 else 1e-3
        try:
            pts.append([round(x, 4), round(float(ev(fn, {**env, 'x': x})), 4)])
        except CalcError as e:
            if 'division by zero' not in str(e):
                raise
    return pts


def sawtooth(g, env):
    """inventory sawtooth: level falls from top to base over each cycle, then jumps back up"""
    q, cyc, base = ev(g['Q'], env), int(ev(g.get('cycles', 4), env)), ev(g.get('base', 0), env)
    T = ev(g['T'], env)
    pts = []
    for c in range(cyc):
        pts += [[round(c * T, 4), round(base + q, 4)], [round((c + 1) * T, 4), round(base, 4)]]
    return pts


def numeric(v, env):
    return ev(v, env) if isinstance(v, str) else v


def apply(spec, style='international'):
    """returns (filled spec, computed vars, problems)"""
    problems = []
    try:
        env, vars_out = solve(spec.get('vars', {}))
    except CalcError as e:
        return spec, {}, [f'vars: {e}']
    for c in spec.get('checks', []):
        try:
            if not ev(c['expr'], env):
                problems.append(f'check failed: {c["expr"]} ({c.get("note", "")})')
        except CalcError as e:
            problems.append(f'check error: {e}')
    missing = set()
    out = fill(spec, env, style, missing=missing)
    if missing:
        problems.append('undefined placeholders: ' + ', '.join(sorted(missing)))
    for sc in out.get('scenes', []):
        if sc.get('type') != 'chart':
            continue
        try:
            for ax in ('x', 'y'):
                for k in ('min', 'max'):
                    sc[ax][k] = numeric(sc[ax][k], env)
                if 'ticks' in sc[ax]:
                    sc[ax]['ticks'] = [numeric(t, env) for t in sc[ax]['ticks']]
            for sr in sc.get('series', []):
                if 'fn' in sr:
                    sr['points'] = sample(sr['fn'], env, numeric(sr.get('from', sc['x']['min']), env), numeric(sr.get('to', sc['x']['max']), env), sr.get('n', 80))
                elif 'gen' in sr:
                    sr['points'] = sawtooth(sr['gen'], env)
                else:
                    sr['points'] = [[numeric(a, env), numeric(b, env)] for a, b in sr['points']]
            for m in sc.get('marks', []):
                m['x'] = numeric(m['x'], env)
                if 'y' in m:
                    m['y'] = numeric(m['y'], env)
        except (CalcError, KeyError, TypeError) as e:
            problems.append(f'chart {sc.get("id")}: {e}')
    return out, vars_out, problems
