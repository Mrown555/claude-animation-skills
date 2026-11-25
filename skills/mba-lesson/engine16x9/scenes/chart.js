// chart: line charts and cost curves (points come from studio/calc.py, which samples formulas exactly),
// optional marked points (e.g. the EOQ minimum) and a notes column on the right. Draw style follows the /graph skill.
(function () {
  const { h, s, tex, rich, reveal, reg } = STUDIO;
  const Q = (el, tag) => { el.dataset.qc = tag; return el; };
  const PAL = ['var(--accent)', 'var(--accent2)', 'var(--accent3)', 'var(--good)', 'var(--bad)'];
  function nice(min, max, n = 5) {
    const span = max - min || 1, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(st => st >= step0) || 10 * mag;
    const out = []; for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(10)); return out;
  }
  const fmt = v => Math.abs(v) >= 1000 ? v.toLocaleString('en-IN') : (+v.toFixed(2)).toString();

  reg('chart', (ctx, sp) => {
    const a = ctx.area();
    const head = Q(h('div', { class: 'h2', html: rich(sp.heading) }), 'heading'); a.append(head);
    const notes = sp.notes || [];
    const CW = notes.length ? 1130 : 1700, CH = 620, L = 150, R = 40, T = 30, B = 90;
    const svg = s('svg', { width: CW, height: CH, viewBox: `0 0 ${CW} ${CH}`, style: 'position:absolute;left:0;top:140px;overflow:visible' });
    a.append(svg);
    const X = sp.x, Y = sp.y;
    const px = x => L + (x - X.min) / (X.max - X.min) * (CW - L - R), py = y => CH - B - (y - Y.min) / (Y.max - Y.min) * (CH - T - B);
    const g = s('g', {}, svg);
    for (const v of (Y.ticks || nice(Y.min, Y.max))) {
      s('line', { x1: L, x2: CW - R, y1: py(v), y2: py(v), stroke: 'var(--line)', 'stroke-width': 2 }, g);
      const tl = s('text', { x: L - 16, y: py(v) + 9, 'text-anchor': 'end', style: "font:500 24px 'Inter';fill:var(--mute)" }, g); tl.textContent = fmt(v);
    }
    for (const v of (X.ticks || nice(X.min, X.max, 6))) {
      const tl = s('text', { x: px(v), y: CH - B + 38, 'text-anchor': 'middle', style: "font:500 24px 'Inter';fill:var(--mute)" }, g); tl.textContent = fmt(v);
    }
    s('line', { x1: L, x2: CW - R, y1: py(Y.min), y2: py(Y.min), stroke: 'var(--ink)', 'stroke-width': 3 }, g);
    s('line', { x1: L, x2: L, y1: T, y2: py(Y.min), stroke: 'var(--ink)', 'stroke-width': 3 }, g);
    const xl = s('text', { x: (L + CW - R) / 2, y: CH - 8, 'text-anchor': 'middle', style: "font:600 26px 'Inter';fill:var(--ink)" }, g); xl.textContent = X.label || '';
    const yl = s('text', { x: 0, y: 0, transform: `translate(14,${(T + py(Y.min)) / 2}) rotate(-90)`, 'text-anchor': 'middle', style: "font:600 26px 'Inter';fill:var(--ink)" }, g); yl.textContent = Y.label || '';
    const legend = h('div', { style: { position: 'absolute', left: L + 'px', top: '74px', display: 'flex', gap: '34px', flexWrap: 'wrap', width: CW - L + 'px' } });
    a.append(legend);
    const ser = (sp.series || []).map((sr, i) => {
      const col = sr.color || PAL[i % PAL.length];
      const d = sr.points.map((p, j) => (j ? 'L' : 'M') + px(p[0]).toFixed(1) + ',' + py(p[1]).toFixed(1)).join(' ');
      const path = s('path', { d, fill: 'none', stroke: col, 'stroke-width': sr.width || 6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, svg);
      if (sr.dash) path.setAttribute('stroke-dasharray', '14 12');
      const len = path.getTotalLength();
      const last = sr.points[sr.labelAt != null ? sr.labelAt : sr.points.length - 1];
      let lab;
      if (sr.labelOnCurve) {
        lab = s('text', { x: px(last[0]) + (sr.labelDx || 12), y: py(last[1]) + (sr.labelDy || -14), 'text-anchor': sr.labelAnchor || 'end', style: `font:700 26px 'Inter';fill:${col}` }, svg);
        lab.textContent = sr.name || '';
      } else {
        lab = Q(h('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', font: "600 26px 'Inter'", color: col } }), 'legend');
        lab.innerHTML = `<span style="width:40px;height:0;border-top:${sr.dash ? '5px dashed' : '6px solid'} ${col}"></span>${rich(sr.name || '')}`;
        legend.append(lab);
      }
      return { path, len, lab, dash: !!sr.dash, p: ctx.tw(ctx.cue(sr, 0), sr.drawTime || 1.6, 'inOut') };
    });
    const marks = (sp.marks || []).map(m => {
      const grp = s('g', {}, svg);
      const yv = m.y != null ? m.y : Y.min;
      s('line', { x1: px(m.x), x2: px(m.x), y1: py(yv), y2: py(Y.min), stroke: 'var(--ink)', 'stroke-width': 3, 'stroke-dasharray': '6 8' }, grp);
      s('circle', { cx: px(m.x), cy: py(yv), r: 12, fill: 'var(--ink)', stroke: '#fff', 'stroke-width': 4 }, grp);
      const lb = s('text', { x: px(m.x) + (m.dx || 0), y: py(yv) - 26 + (m.dy || 0), 'text-anchor': 'middle', style: "font:700 28px 'Inter';fill:var(--ink)" }, grp);
      lb.textContent = m.label || ''; lb.dataset.qc = 'mark';
      return { grp, p: ctx.tw(ctx.cue(m, 1), .6, 'back') };
    });
    const col = h('div', { style: { position: 'absolute', left: '1200px', top: '120px', width: '528px', display: 'flex', flexDirection: 'column', gap: '26px' } });
    const nrows = notes.map((n, i) => { const r = Q(h('div', { class: 'card', html: rich(n.text), style: { padding: '22px 26px', font: "500 28px/1.35 'Inter'", borderLeft: `8px solid ${n.color || PAL[i % PAL.length]}` } }), 'note'); col.append(r); return [r, ctx.tw(ctx.cue(n, i), .6)]; });
    if (notes.length) a.append(col);
    const ph = ctx.tw(.3, .6);
    return t => {
      reveal(head, ph(t)); g.style.opacity = ph(t);
      ser.forEach(x => { const p = x.p(t); if (!x.dash) { x.path.setAttribute('stroke-dasharray', x.len); x.path.setAttribute('stroke-dashoffset', x.len * (1 - p)); } else x.path.style.opacity = p; x.path.style.visibility = p > 0 ? 'visible' : 'hidden'; x.lab.style.opacity = sp.series.length && x.lab.tagName === 'DIV' ? Math.min(1, p * 4) : Math.max(0, p * 3 - 2); });
      marks.forEach(m => { const p = m.p(t); m.grp.style.opacity = Math.min(1, p * 1.5); });
      nrows.forEach(([r, p]) => reveal(r, p(t), 0, 24));
    };
  });
})();
