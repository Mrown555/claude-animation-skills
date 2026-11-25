// Maths scenes. Numbers in these specs are filled in by studio/calc.py ({{var}} placeholders) before rendering,
// so what is shown and what is narrated always come from the same verified computation.
(function () {
  const { h, tex, rich, reveal, reg } = STUDIO;
  const Q = (el, tag) => { el.dataset.qc = tag; return el; };
  const wipe = (el, p) => { el.style.opacity = p > 0 ? 1 : 0; el.style.clipPath = p >= 1 ? '' : `inset(-20px ${100 - p * 100}% -20px -20px)`; };

  // formula: the expression appears dimmed, then each term lights up with its meaning (\htmlClass{t1}{D} ... in the TeX)
  reg('formula', (ctx, sp) => {
    const a = ctx.area();
    const head = Q(h('div', { class: 'h2', html: rich(sp.heading || 'The formula') }), 'heading');
    const box = h('div', { class: 'card', style: { marginTop: '36px', padding: '40px 50px', display: 'flex', justifyContent: 'center', fontSize: (sp.size || 64) + 'px' } });
    const fx = Q(h('div', { html: tex(sp.latex, true) }), 'formula');
    box.append(fx); a.append(head, box);
    const terms = sp.terms || [];
    const legend = h('div', { style: { marginTop: '34px', display: 'grid', gridTemplateColumns: terms.length > 3 ? '1fr 1fr' : '1fr', gap: '18px 40px' } });
    const rows = terms.map((tm, i) => {
      const r = Q(h('div', { class: 'body', style: { display: 'flex', alignItems: 'baseline', gap: '22px', fontSize: '31px' } }), 'term');
      r.innerHTML = `<span style="min-width:120px;text-align:right;color:var(--accent);font-size:38px">${tex(tm.sym)}</span><span>${rich(tm.label)}</span>`;
      legend.append(r);
      return { r, els: () => fx.querySelectorAll('.t' + (i + 1)), p: ctx.tw(ctx.cue(tm, i + 1), .6) };
    });
    a.append(legend);
    const ph = ctx.tw(.3, .6), pf = ctx.tw(ctx.cue({ at: sp.formulaAt ?? 0, delay: sp.formulaDelay ?? 1.0 }), .9);
    const pfin = sp.finalAt != null ? ctx.tw(ctx.cue({ at: sp.finalAt }), .6) : null;
    const nodes = rows.map(x => [...x.els()]);
    return t => {
      reveal(head, ph(t)); wipe(fx, pf(t));
      rows.forEach((x, i) => {
        const p = x.p(t); reveal(x.r, p, 0, 24);
        nodes[i].forEach(n => { n.style.opacity = .22 + .78 * p; n.style.color = p > 0 ? 'var(--accent)' : ''; });
      });
      if (pfin) { const p = pfin(t); box.style.boxShadow = `0 0 0 ${6 * p}px var(--accent), 0 10px 40px rgba(27,35,51,.08)`; }
    };
  });

  // calc: given values on the left, the working line by line on the right, the answer boxed at the end
  reg('calc', (ctx, sp) => {
    const a = ctx.area();
    const head = Q(h('div', { class: 'h2', html: rich(sp.heading || 'Worked example') }), 'heading'); a.append(head);
    const given = sp.given || [];
    const gcard = h('div', { class: 'card', style: { position: 'absolute', left: 0, top: '96px', width: '600px', padding: '30px 34px' } });
    gcard.append(h('div', { class: 'kicker', text: 'Given' }));
    const grows = given.map(g => {
      const r = Q(h('div', { style: { display: 'flex', alignItems: 'baseline', gap: '16px', marginTop: '20px', font: "500 28px/1.3 'Inter'" } }), 'given');
      r.innerHTML = `<span style="min-width:70px;color:var(--accent);font-size:34px">${tex(g.sym)}</span><span style="flex:1">${rich(g.label)}</span><span class="mono" style="font-weight:500;white-space:nowrap">${rich(g.value)}</span>`;
      gcard.append(r); return [r, ctx.tw(ctx.cue(g, 0), .5)];
    });
    if (given.length) a.append(gcard);
    const ns = (sp.steps || []).length, two = !given.length && ns >= 4;   // many steps and no "given" card: two columns
    const work = h('div', { style: { position: 'absolute', left: given.length ? '660px' : '0', top: '96px', right: 0, display: two ? 'grid' : 'flex', gridTemplateColumns: '1fr 1fr', flexDirection: 'column', gap: two ? '30px 60px' : (ns > 3 ? '12px' : '22px') } });
    const fsz = ns > 3 && !two ? 34 : 40;
    const steps = (sp.steps || []).map((st, i) => {
      const r = h('div', {});
      if (st.note) r.append(Q(h('div', { class: 'small', html: rich(st.note), style: { fontSize: '25px', marginBottom: '2px' } }), 'note'));
      const m = Q(h('div', { html: tex(st.tex, false), style: { fontSize: fsz + 'px' } }), 'step');
      r.append(m); work.append(r);
      return [r, m, ctx.tw(ctx.cue(st, i + 1), .9, 'inOut')];
    });
    a.append(work);
    let res = null, pres = null;
    if (sp.result) {
      res = Q(h('div', { style: { gridColumn: '1 / -1', marginTop: '12px', padding: '20px 30px', borderRadius: '18px', background: 'var(--soft)', border: '4px solid var(--accent)', display: 'flex', alignItems: 'center', gap: '30px' } }), 'result');
      res.innerHTML = `<span style="font-size:44px">${tex(sp.result.tex)}</span>` + (sp.result.text ? `<span class="body" style="font-size:28px">${rich(sp.result.text)}</span>` : '');
      work.append(res); pres = ctx.tw(ctx.cue(sp.result, steps.length + 1), .6, 'back');
    }
    const ph = ctx.tw(.3, .6), pg = ctx.tw(.5, .6);
    return t => {
      reveal(head, ph(t)); reveal(gcard, pg(t), 20);
      grows.forEach(([r, p]) => reveal(r, p(t), 0, 20));
      steps.forEach(([r, m, p]) => { const v = p(t); const n = r.firstChild !== m ? r.firstChild : null; if (n) n.style.opacity = v > 0 ? Math.min(1, v * 3) : 0; wipe(m, v); });
      if (res) { const p = pres(t); res.style.opacity = Math.min(1, p * 2); res.style.transform = `scale(${.92 + .08 * p})`; res.style.transformOrigin = 'left center'; }
    };
  });
})();
