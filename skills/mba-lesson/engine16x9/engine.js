// MBA Animation Studio: 16:9 engine core. Every frame is a pure function of (scene, t), so any frame can be rendered
// in any order by any worker. Scenes register a builder; builders declare their animation spans through ctx.tw(), and
// the renderer re-captures only frames inside those spans (static holds reuse the previous frame).
// Wrapped in an IIFE: lib.js/chars.js (stick-figure skill) already declare globals like W, H, clamp, ease.
(function () {
  const W = 1920, H = 1080, FPS = 30, FADE_IN = .45, FADE_OUT = .35;
  const cl = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const EASE = {
    out: t => 1 - Math.pow(1 - t, 3), in: t => t * t * t, lin: t => t,
    inOut: t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
    back: t => { const c1 = 1.6, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  };
  const REG = {};

  function h(tag, attrs = {}, kids = []) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') el.className = v; else if (k === 'html') el.innerHTML = v; else if (k === 'text') el.textContent = v;
      else if (k === 'style') Object.assign(el.style, v); else el.setAttribute(k, v);
    }
    for (const c of [].concat(kids)) if (c != null) el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    return el;
  }
  const NS = 'http://www.w3.org/2000/svg';
  function s(tag, attrs = {}, parent) {
    const el = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    if (parent) parent.appendChild(el);
    return el;
  }
  // inline maths: text with $...$ segments, or a whole TeX string
  function tex(str, display = false) {
    return katex.renderToString(str, { displayMode: display, throwOnError: false, trust: true, strict: 'ignore', output: 'html' });
  }
  function rich(str) {
    const esc = x => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\*\*(.+?)\*\*/g, '<span class="hl">$1</span>');
    return String(str ?? '').split(/(\$[^$]+\$)/).map(p => p.startsWith('$') && p.endsWith('$') && p.length > 2 ? tex(p.slice(1, -1)) : esc(p)).join('');
  }
  function reveal(el, p, dy = 26, dx = 0) {
    el.style.opacity = p; el.style.transform = p >= 1 ? '' : `translate(${(1 - p) * dx}px,${(1 - p) * dy}px)`;
  }
  // shrink a box's font until its content fits (QC flags anything still overflowing)
  function fit(el, minPx = 22) {
    let fs = parseFloat(getComputedStyle(el).fontSize);
    while ((el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1) && fs > minPx) { fs -= 1; el.style.fontSize = fs + 'px'; }
  }

  class Ctx {
    constructor(spec, timing, root) { this.spec = spec; this.timing = timing; this.root = root; this.iv = []; this.dur = timing.dur; }
    // time of a cue: item.at = sentence index (default 0), item.delay = seconds after that sentence starts
    cue(item, dflt = 0) {
      const sent = this.timing.sent;
      const at = item && item.at != null ? item.at : dflt;
      const i = cl(Math.round(at), 0, sent.length - 1);
      return (sent[i] ? sent[i].s : 0) + (item && item.delay != null ? item.delay : (at === 0 ? FADE_IN + .15 : .1));
    }
    tw(t0, d = .6, e = 'out') { this.iv.push([t0, t0 + d]); const f = EASE[e] || EASE.out; return t => f(cl((t - t0) / d)); }
    loop(t0 = 0, t1 = this.dur) { this.iv.push([t0, t1]); }
    area(cls = '') { const a = h('div', { class: 'area ' + cls }); this.root.appendChild(a); return a; }
  }

  let cur = { i: -1, update: null, ctx: null };
  function load(i) {
    const L = window.LESSON, sc = L.scenes[i];
    const root = document.getElementById('scene'); root.innerHTML = '';
    document.getElementById('fade').style.opacity = 0;
    const ctx = new Ctx(sc.spec, sc.timing, root);
    const b = REG[sc.spec.type];
    if (!b) throw new Error('unknown scene type ' + sc.spec.type);
    const update = b(ctx, sc.spec) || (() => {});
    // chrome: lesson tag + source tag (traceability on screen)
    document.getElementById('lessonTag').innerHTML = `<b>${L.lesson.id}</b> &nbsp;${rich(L.lesson.title)}`;
    const st = document.getElementById('sourceTag');
    const src = sc.spec.source || {};
    st.className = sc.spec.supplementary ? 'supp' : '';
    st.textContent = sc.spec.supplementary ? 'Beyond the notes' : (src.pages && src.pages.length ? 'Notes · p. ' + src.pages.join(', ') : '');
    ctx.iv.push([0, FADE_IN], [sc.timing.dur - FADE_OUT, sc.timing.dur]);
    for (const sb of sc.timing.subs) ctx.iv.push([sb.s, sb.s + .001], [sb.e, sb.e + .001]);
    cur = { i, update, ctx, subs: sc.timing.subs };
    return { frames: sc.timing.frames, dur: sc.timing.dur, iv: ctx.iv };
  }
  function frame(f) {
    const t = f / FPS, c = cur;
    c.update(t);
    const sub = c.subs.find(x => t >= x.s && t < x.e);
    const st = document.getElementById('subText'); const txt = sub ? sub.text : '';
    if (st.textContent !== txt) st.textContent = txt;
    const fin = cl(t / FADE_IN), fout = cl((c.ctx.dur - t) / FADE_OUT);
    document.getElementById('scene').style.opacity = EASE.out(fin) * EASE.out(fout);
    document.getElementById('scene').style.transform = `scale(${1 - .015 * (1 - EASE.out(fin))})`;
  }
  // layout QC on the current frame: off-frame, overflow, tiny text, overlaps, subtitle-band intrusion
  function qc() {
    const out = [];
    const els = [...document.querySelectorAll('#scene [data-qc]')].filter(e => {
      let o = 1, n = e; while (n && n !== document.body) { o *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; }
      return o > .5 && e.getBoundingClientRect().width > 0;
    });
    const name = e => (e.dataset.qc || e.tagName) + ': "' + (e.textContent || '').trim().slice(0, 40) + '"';
    for (const e of els) {
      const r = e.getBoundingClientRect();
      if (r.left < 40 || r.top < 90 || r.right > W - 40 || r.bottom > 912) out.push({ kind: 'off-area', el: name(e), rect: [r.left, r.top, r.right, r.bottom].map(Math.round) });
      if (e.scrollHeight > e.clientHeight + 3 || e.scrollWidth > e.clientWidth + 3) {
        if (getComputedStyle(e).overflow !== 'visible' || e.dataset.fit) out.push({ kind: 'overflow', el: name(e) });
      }
      // smallest font that actually carries text inside this element (KaTeX sub/superscripts excluded)
      let fs = 1e9; const tw = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
      for (let n = tw.nextNode(); n; n = tw.nextNode()) { if (!n.textContent.replace(/[\s\u200b\u00a0]/g, '') || n.parentElement.closest('.msupsub, .vlist-s')) continue; fs = Math.min(fs, parseFloat(getComputedStyle(n.parentElement).fontSize)); }
      if (fs < 22) out.push({ kind: 'small-text', el: name(e), px: fs });
    }
    for (let a = 0; a < els.length; a++) for (let b = a + 1; b < els.length; b++) {
      const A = els[a], B = els[b]; if (A.contains(B) || B.contains(A)) continue;
      const r1 = A.getBoundingClientRect(), r2 = B.getBoundingClientRect();
      const ix = Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left), iy = Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top);
      if (ix > 4 && iy > 4 && ix * iy > .03 * Math.min(r1.width * r1.height, r2.width * r2.height)) out.push({ kind: 'overlap', a: name(A), b: name(B) });
    }
    return out;
  }
  function space() {
    const NS_ = 'http://www.w3.org/2000/svg'; let seed = 7;
    const R = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    let g = '';
    for (let i = 0; i < 150; i++) { const x = R() * W, y = R() * H, r = .7 + R() * 1.9; g += `<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r.toFixed(1)}" fill="${R() > .45 ? '#fff' : '#b9a6ff'}" opacity="${(.25 + R() * .4).toFixed(2)}"/>`; }
    const spark = (x, y, s) => `<path d="M${x},${y - s} Q${x},${y} ${x + s},${y} Q${x},${y} ${x},${y + s} Q${x},${y} ${x - s},${y} Q${x},${y} ${x},${y - s}Z" fill="#fff" opacity=".8"/>`;
    g += spark(150, 980, 16) + spark(1840, 70, 14) + spark(1020, 1040, 11) + spark(60, 520, 12) + spark(1880, 520, 12);
    const bands = [-210, -120, -30, 70, 160, 250].map((y, i) => `<rect x="-340" y="${y}" width="680" height="${i % 2 ? 34 : 54}" fill="${i % 2 ? '#8a64ff' : '#4d2fb8'}" opacity=".7"/>`).join('');
    document.getElementById('bgfx').innerHTML = `<svg xmlns="${NS_}" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
      <defs><radialGradient id="haze1" cx="20%" cy="15%" r="60%"><stop offset="0" stop-color="#5b2fd0" stop-opacity=".35"/><stop offset="1" stop-color="#5b2fd0" stop-opacity="0"/></radialGradient>
      <radialGradient id="halo"><stop offset=".68" stop-color="#8c5cff" stop-opacity=".38"/><stop offset="1" stop-color="#8c5cff" stop-opacity="0"/></radialGradient>
      <clipPath id="pc"><circle r="330"/></clipPath>
      <mask id="night"><rect x="-400" y="-400" width="800" height="800" fill="#fff"/><circle cx="75" r="330" fill="#000"/></mask></defs>
      <rect width="${W}" height="${H}" fill="url(#haze1)"/>${g}
      <g transform="translate(1660,1175)"><circle r="480" fill="url(#halo)"/><circle r="330" fill="#6c47e0"/>
        <g clip-path="url(#pc)">${bands}<circle r="330" fill="#140c46" opacity=".6" mask="url(#night)"/></g></g></svg>`;
  }
  function init() {
    const a = window.LESSON.theme || {};
    const style = window.LESSON.style || 'clean'; document.documentElement.dataset.style = style; if (style === 'kurzgesagt') space();
    for (const [k, v] of Object.entries(a)) document.documentElement.style.setProperty('--' + k, v);
    window.STUDIO.ready = document.fonts.ready.then(async () => {
      await Promise.all(['500 30px Inter', '600 30px Inter', '700 30px Inter', '700 30px "Inter Tight"', '700 30px Poppins', '600 30px Poppins', '800 30px "Inter Tight"', '500 30px "JetBrains Mono"', '30px KaTeX_Main', 'italic 30px KaTeX_Math'].map(f => document.fonts.load(f)));
      return true;
    });
  }
  window.STUDIO = { W, H, FPS, EASE, cl, h, s, tex, rich, reveal, fit, reg: (n, f) => { REG[n] = f; }, load, frame, qc, init,
    // browser preview: index.html?scene=2&t=4.5
    preview: async () => { await window.STUDIO.ready; const q = new URLSearchParams(location.search); load(+(q.get('scene') || 0)); frame(Math.round(+(q.get('t') || 3) * FPS)); } };
})();
