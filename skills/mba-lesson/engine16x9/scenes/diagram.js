// Diagram scenes: process (steps joined by drawing arrows, with an optional travelling token) and matrix (2x2 frameworks).
(function () {
  const { h, s, rich, reveal, reg, cl } = STUDIO;
  const Q = (el, tag) => { el.dataset.qc = tag; return el; };
  const PAL = ['var(--accent)', 'var(--accent2)', 'var(--accent3)', 'var(--good)', 'var(--bad)'];

  reg('process', (ctx, sp) => {
    const a = ctx.area();
    const head = Q(h('div', { class: 'h2', html: rich(sp.heading) }), 'heading'); a.append(head);
    const st = sp.steps || [], n = st.length, GAP = 70, BW = (1728 - GAP * (n - 1)) / n, TOP = 200, BH = 440;
    const svg = s('svg', { width: 1728, height: 790, style: 'position:absolute;left:0;top:0;overflow:visible' }); a.append(svg);
    const boxes = st.map((x, i) => {
      const b = h('div', { class: 'card', style: { position: 'absolute', left: i * (BW + GAP) + 'px', top: TOP + 'px', width: BW + 'px', height: BH + 'px', padding: '30px 28px', borderTop: `10px solid ${PAL[i % PAL.length]}` } });
      b.append(h('div', { class: 'pill', text: x.label || 'Step ' + (i + 1), style: { background: 'var(--soft)' } }),
        Q(h('div', { class: 'h2', html: rich(x.title), style: { fontSize: n > 4 ? '34px' : '40px', marginTop: '18px' } }), 'step-title'),
        Q(h('div', { class: 'body', html: rich(x.text || ''), style: { fontSize: n > 4 ? '25px' : '28px', marginTop: '16px', color: 'var(--mute)' } }), 'step-text'));
      a.append(b); return [b, ctx.tw(ctx.cue(x, i), .6, 'back')];
    });
    const arrows = st.slice(1).map((x, i) => {
      const x0 = (i + 1) * (BW + GAP) - GAP + 8, x1 = (i + 1) * (BW + GAP) - 12, y = TOP + BH / 2;
      const ln = s('path', { d: `M${x0},${y} L${x1},${y}`, stroke: 'var(--ink)', 'stroke-width': 5, fill: 'none', 'stroke-linecap': 'round' }, svg);
      const hd = s('path', { d: `M${x1 - 14},${y - 12} L${x1},${y} L${x1 - 14},${y + 12}`, stroke: 'var(--ink)', 'stroke-width': 5, fill: 'none', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, svg);
      const t0 = ctx.cue(st[i + 1], i + 1) - .35; return { ln, hd, len: x1 - x0, p: ctx.tw(t0, .35) };
    });
    let loop = null;
    if (sp.loop && n > 1) {
      const xs = BW / 2, xe = (n - 1) * (BW + GAP) + BW / 2, y0 = TOP + BH + 14, y1 = TOP + BH + 80;
      const d = `M${xe},${y0} L${xe},${y1} L${xs},${y1} L${xs},${y0 + 6}`;
      const ln = s('path', { d, stroke: 'var(--accent)', 'stroke-width': 5, fill: 'none', 'stroke-dasharray': '' }, svg);
      const lb = s('text', { x: (xs + xe) / 2, y: y1 + 40, 'text-anchor': 'middle', style: "font:600 26px 'Inter';fill:var(--accent)" }, svg); lb.textContent = sp.loop === true ? 'repeat' : sp.loop;
      const len = ln.getTotalLength(); loop = { ln, lb, len, p: ctx.tw(ctx.cue({ at: sp.loopAt ?? (n - 1), delay: 1.2 }), 1.0, 'inOut') };
    }
    const ph = ctx.tw(.3, .6);
    return t => {
      reveal(head, ph(t)); boxes.forEach(([b, p]) => { const v = p(t); b.style.opacity = Math.min(1, v * 1.4); b.style.transform = `translateY(${(1 - v) * 30}px) scale(${.94 + .06 * v})`; });
      arrows.forEach(ar => { const p = ar.p(t); ar.ln.setAttribute('stroke-dasharray', ar.len); ar.ln.setAttribute('stroke-dashoffset', ar.len * (1 - p)); ar.hd.style.opacity = p >= 1 ? 1 : 0; ar.ln.style.opacity = p > 0 ? 1 : 0; });
      if (loop) { const p = loop.p(t); loop.ln.setAttribute('stroke-dasharray', loop.len); loop.ln.setAttribute('stroke-dashoffset', loop.len * (1 - p)); loop.ln.style.opacity = p > 0 ? 1 : 0; loop.lb.style.opacity = p; }
    };
  });

  reg('matrix', (ctx, sp) => {
    const a = ctx.area();
    const head = Q(h('div', { class: 'h2', html: rich(sp.heading) }), 'heading'); a.append(head);
    const X0 = 220, Y0 = 100, CW = 690, CH = 300, G = 20;
    const cells = (sp.cells || []).slice(0, 4).map((c, i) => {
      const r = Math.floor(i / 2), k = i % 2;
      const b = h('div', { class: 'card', style: { position: 'absolute', left: X0 + k * (CW + G) + 'px', top: Y0 + r * (CH + G) + 'px', width: CW + 'px', height: CH + 'px', borderLeft: `10px solid ${c.color || PAL[i]}` } });
      b.append(Q(h('div', { class: 'h2', html: rich(c.title), style: { fontSize: '40px' } }), 'cell-title'), Q(h('div', { class: 'body', html: rich(c.text || ''), style: { fontSize: '27px', marginTop: '14px', color: 'var(--mute)' } }), 'cell-text'));
      a.append(b); return [b, ctx.tw(ctx.cue(c, i), .6, 'back')];
    });
    const xl = Q(h('div', { class: 'small', html: rich(sp.xlabel || ''), style: { position: 'absolute', left: X0 + 'px', width: 2 * CW + G + 'px', top: Y0 + 2 * CH + G + 16 + 'px', textAlign: 'center', fontWeight: 700, color: 'var(--ink)' } }), 'axis');
    const yl = Q(h('div', { class: 'small', html: rich(sp.ylabel || ''), style: { position: 'absolute', left: '0px', width: '190px', top: Y0 + CH - 20 + 'px', textAlign: 'right', fontWeight: 700, color: 'var(--ink)' } }), 'axis');
    a.append(xl, yl);
    const ph = ctx.tw(.3, .6);
    return t => { reveal(head, ph(t)); reveal(xl, ph(t)); reveal(yl, ph(t)); cells.forEach(([b, p]) => { const v = p(t); b.style.opacity = cl(v * 1.4); b.style.transform = `scale(${.92 + .08 * v})`; }); };
  });
})();
