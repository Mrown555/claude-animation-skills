// roleplay: two stick-figure characters (the original /stick-figure rig, drawStick from chars.js, reused unchanged)
// in a simple setting, with speech bubbles timed to narration sentences. For HR conversations, sales calls, negotiations.
(function () {
  const { h, rich, reveal, reg, cl } = STUDIO;
  const Q = (el, tag) => { el.dataset.qc = tag; return el; };
  const CW = 1728, CH = 790, FLOOR = 690;
  function setting(c, kind) {
    c.fillStyle = '#efe9df'; c.fillRect(0, 0, CW, CH);
    c.fillStyle = '#e2d9cb'; c.fillRect(0, FLOOR - 10, CW, CH - FLOOR + 10);
    if (kind === 'office' || kind === 'store') {
      c.fillStyle = '#cfe3ee'; c.fillRect(660, 70, 410, 260); c.strokeStyle = '#2a3242'; c.lineWidth = 8; c.strokeRect(660, 70, 410, 260);
      c.beginPath(); c.moveTo(865, 70); c.lineTo(865, 330); c.stroke();
    }
    if (kind === 'office') { c.fillStyle = '#b98a5e'; c.fillRect(640, 560, 450, 30); c.fillRect(670, 590, 24, 150); c.fillRect(1036, 590, 24, 150); }
    if (kind === 'store') { c.fillStyle = '#c9a274'; for (let k = 0; k < 3; k++) { c.fillRect(700, 420 + k * 100, 340, 18); } c.fillStyle = '#e2763a'; for (let k = 0; k < 9; k++) c.fillRect(712 + (k % 3) * 110, 372 + Math.floor(k / 3) * 100, 70, 48); }
  }
  // plain office clothes: one solid colour, no pirate hat (the rig's default)
  const solid = c => { const k = (PAL[c] || [c])[0]; return [k, k]; };
  reg('roleplay', (ctx, sp) => {
    const a = ctx.area();
    const cv = h('canvas', { width: CW, height: CH, style: { position: 'absolute', left: 0, top: 0, borderRadius: '24px' } }); a.append(cv);
    const c = cv.getContext('2d');
    const chars = (sp.characters || []).slice(0, 2).map((ch, i) => ({
      name: ch.name, x: i === 0 ? 380 : 1350, flip: i === 0 ? 1 : -1, cols: solid(ch.color || (i === 0 ? 'blue' : 'red')),
    }));
    const tags = chars.map(ch => { const tg = Q(h('div', { class: 'pill', text: ch.name, style: { position: 'absolute', left: ch.x - 170 + 'px', width: '340px', textAlign: 'center', top: FLOOR + 14 + 'px', background: '#fff', color: 'var(--ink)' } }), 'name'); a.append(tg); return tg; });
    const sent = ctx.timing.sent;
    const lines = (sp.lines || []).map((ln, k) => {
      const who = ln.who || 0, ch = chars[who];
      const b = Q(h('div', { class: 'card', html: rich(ln.text), style: { position: 'absolute', top: '40px', width: '640px', font: "600 30px/1.35 'Inter'", padding: '26px 30px', [who === 0 ? 'left' : 'right']: '40px' } }), 'bubble');
      a.append(b);
      const s0 = ctx.cue(ln, k), si = cl(Math.round(ln.at ?? k), 0, sent.length - 1);
      return { b, who, s0, talkEnd: sent[si] ? sent[si].e : s0 + 2, p: ctx.tw(s0, .4, 'back') };
    });
    lines.forEach((l, k) => { const nx = lines.slice(k + 1).find(m => m.who === l.who); l.hideAt = nx ? nx.s0 : 1e9; if (nx) ctx.tw(nx.s0 - .01, .01); });
    ctx.loop();                                     // idle motion: every frame changes
    const ph = ctx.tw(.2, .6);
    return t => {
      setting(c, sp.setting || 'office');
      chars.forEach((ch, i) => {
        const talking = lines.some(l => l.who === i && t >= l.s0 && t < l.talkEnd);
        const mouth = talking ? (Math.floor(t * 9 + i) % 2 ? 'o' : 'smile') : (sp.mood && sp.mood[i]) || 'smile';
        const bob = Math.sin(t * 2.2 + i * 1.7) * .006;
        drawStick(c, { hat: 'none', belt: false, x: ch.x, y: FLOOR, s: 360, flip: ch.flip, cols: ch.cols, bob, face: { eyes: 'normal', look: [.5 * ch.flip, 0], mouth, blink: (t + i * .7) % 3.6 < .12 ? 1 : 0 },
          arms: talking ? { L: [.35, -.15], R: [1.4 + Math.sin(t * 5) * .25, -.6] } : { L: [.3, -.1], R: [.3, -.1] } });
      });
      cv.style.opacity = ph(t); tags.forEach(tg => reveal(tg, ph(t)));
      lines.forEach(l => { const p = t >= l.hideAt ? 0 : l.p(t); l.b.style.opacity = cl(p * 1.5); l.b.style.transform = `scale(${.9 + .1 * p})`; });
    };
  });
})();
