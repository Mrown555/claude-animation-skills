// Text-led scenes: title, concept (definition), bullets (key points / recap / story with a callout), table (comparisons).
(function () {
  const { h, rich, reveal, fit, reg } = STUDIO;
  const Q = (el, tag) => { el.dataset.qc = tag; return el; };

  reg('title', (ctx, sp) => {
    const a = ctx.area();
    Object.assign(a.style, { display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'flex-start', paddingLeft: '40px' });
    const k = Q(h('div', { class: 'kicker', html: rich(sp.kicker || '') }), 'kicker');
    const ti = Q(h('div', { class: 'h1', html: rich(sp.title), style: { fontSize: '92px', maxWidth: '1500px', marginTop: '24px' } }), 'title');
    const bar = h('div', { style: { height: '8px', width: '0px', background: 'var(--accent)', borderRadius: '4px', marginTop: '40px' } });
    const sub = Q(h('div', { class: 'body', html: rich(sp.subtitle || ''), style: { color: 'var(--mute)', marginTop: '36px', maxWidth: '1400px' } }), 'subtitle');
    a.append(k, ti, bar, sub);
    const pk = ctx.tw(.3, .6), pt = ctx.tw(.45, .8), pb = ctx.tw(.9, .9, 'inOut'), ps = ctx.tw(ctx.cue({ at: sp.subtitleAt ?? 0, delay: 1.2 }), .7);
    return t => { reveal(k, pk(t)); reveal(ti, pt(t), 40); bar.style.width = 260 * pb(t) + 'px'; reveal(sub, ps(t)); };
  });

  reg('concept', (ctx, sp) => {
    const a = ctx.area();
    const pts = sp.points || [];
    const card = h('div', { class: 'card', style: { position: 'absolute', left: '0', top: '40px', width: pts.length ? '900px' : '1500px', minHeight: '520px' } });
    const k = h('div', { class: 'kicker', text: sp.kicker || 'Concept' });
    const term = Q(h('div', { class: 'h1', html: rich(sp.term), style: { marginTop: '18px' } }), 'term');
    const def = Q(h('div', { class: 'body', html: rich(sp.definition), style: { marginTop: '26px' } }), 'definition');
    const gl = sp.gloss ? Q(h('div', { class: 'body', html: '<span class="hl">In simple words:</span> ' + rich(sp.gloss), style: { marginTop: '28px', padding: '22px 26px', background: 'var(--soft)', borderRadius: '16px', fontSize: '30px' } }), 'gloss') : null;
    card.append(k, term, def); if (gl) card.append(gl);
    a.append(card);
    const col = h('div', { style: { position: 'absolute', left: '980px', top: '60px', width: '748px', display: 'flex', flexDirection: 'column', gap: '34px' } });
    const items = pts.map(p => { const r = Q(h('div', { class: 'body', style: { display: 'flex', fontSize: '32px' }, html: '<span class="dot"></span><span>' + rich(p.text) + '</span>' }), 'point'); col.append(r); return [r, ctx.tw(ctx.cue(p, 1), .6)]; });
    a.append(col);
    const pc = ctx.tw(.35, .7), pd = ctx.tw(ctx.cue({ at: sp.definitionAt ?? 0, delay: .9 }), .6), pg = ctx.tw(ctx.cue({ at: sp.glossAt ?? 1, delay: .2 }), .6);
    return t => { reveal(card, pc(t), 30); reveal(def, pd(t), 16); if (gl) reveal(gl, pg(t), 16); items.forEach(([r, p]) => reveal(r, p(t), 0, 30)); };
  });

  reg('bullets', (ctx, sp) => {
    const a = ctx.area();
    const head = Q(h('div', { class: 'h2', html: rich(sp.heading) }), 'heading');
    const k = sp.kicker ? h('div', { class: 'kicker', text: sp.kicker, style: { marginBottom: '14px' } }) : null;
    const wrap = h('div', { style: { position: 'absolute', left: 0, top: 0, width: sp.callout ? '1000px' : '1600px' } });
    if (k) wrap.append(k); wrap.append(head);
    const list = h('div', { style: { marginTop: '44px', display: 'flex', flexDirection: 'column', gap: (sp.items || []).length > 4 ? '24px' : '34px' } });
    const recap = sp.variant === 'recap';
    const rows = (sp.items || []).map((it, n) => {
      const mark = recap ? `<span class="dot" style="background:var(--good)"></span>` : (sp.numbered ? `<span class="pill" style="margin-right:20px;flex:none">${n + 1}</span>` : '<span class="dot"></span>');
      const r = Q(h('div', { class: 'body', style: { display: 'flex', alignItems: 'baseline' }, html: mark + '<span>' + rich(it.text) + (it.sub ? `<div class="small" style="margin-top:6px">${rich(it.sub)}</div>` : '') + '</span>' }), 'item');
      list.append(r); return [r, ctx.tw(ctx.cue(it, n === 0 ? 0 : n), .55)];
    });
    wrap.append(list); a.append(wrap);
    let call = null, pcall = null;
    if (sp.callout) {
      call = h('div', { class: 'card', style: { position: 'absolute', left: '1080px', top: '20px', width: '648px', borderTop: '8px solid var(--accent2)' } });
      call.append(h('div', { class: 'kicker', text: (sp.callout.title || 'Example') + (sp.callout.supplementary ? ' · beyond the notes' : ''), style: { color: 'var(--accent2)' } }),
        Q(h('div', { class: 'body', html: rich(sp.callout.text), style: { marginTop: '18px', fontSize: '30px' } }), 'callout'));
      a.append(call); pcall = ctx.tw(ctx.cue(sp.callout, 1), .7);
    }
    const ph = ctx.tw(.3, .6);
    return t => { reveal(wrap.firstChild, ph(t)); if (k) reveal(head, ph(t)); rows.forEach(([r, p]) => reveal(r, p(t), 0, 28)); if (call) reveal(call, pcall(t), 30); };
  });

  reg('table', (ctx, sp) => {
    const a = ctx.area();
    const head = Q(h('div', { class: 'h2', html: rich(sp.heading) }), 'heading'); a.append(head);
    const cols = sp.columns || [];
    const grid = h('div', { style: { marginTop: '40px', display: 'grid', gridTemplateColumns: (sp.widths || cols.map(() => '1fr')).join(' '), background: 'var(--paper)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 10px 40px rgba(27,35,51,.08)' } });
    const fs = (sp.rows || []).length > 5 ? '26px' : '30px';
    cols.forEach((c, j) => grid.append(Q(h('div', { html: rich(c), style: { padding: '20px 26px', font: "700 28px 'Inter'", background: j === 0 ? 'var(--ink)' : 'var(--accent)', color: '#fff' } }), 'th')));
    const rows = (sp.rows || []).map((r, n) => {
      const cells = r.cells.map((c, j) => Q(h('div', { html: rich(c), style: { padding: '18px 26px', font: `${j === 0 ? 700 : 500} ${fs}/1.3 'Inter'`, borderTop: '1px solid var(--line)', background: r.highlight ? '#fff6e9' : '' } }), 'td'));
      cells.forEach(c => grid.append(c)); return [cells, ctx.tw(ctx.cue(r, n), .5)];
    });
    a.append(grid);
    const ph = ctx.tw(.3, .6);
    return t => { reveal(head, ph(t)); reveal(grid, ph(t), 20); rows.forEach(([cells, p]) => cells.forEach(c => reveal(c, p(t), 0, 20))); };
  });
})();
