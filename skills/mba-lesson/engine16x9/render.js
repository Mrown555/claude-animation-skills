// Playwright frame-stepper for the 16:9 engine (same approach as the stick-figure skill's tools/render.js).
//   node render.js <workdir> <sceneIds|all> [--stills t1,t2]
// <workdir>/lesson-data.js holds window.LESSON. Writes <workdir>/scenes/sNN.mp4 (silent) and sNN.qc.json.
// Frames outside the scene's declared animation spans are not re-captured: the previous JPEG is reused.
// Playwright resolves through NODE_PATH (kit/node_modules on the laptop). CHROME=<path> picks a browser binary.
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');

const ENGINE = __dirname, REPO = path.resolve(ENGINE, '..', '..', '..');
const [work, which, flag, flagVal] = process.argv.slice(2);
const WORK = path.resolve(work);
const ROOTS = { '/engine/': ENGINE, '/kit/': path.join(REPO, 'kit'), '/skills/': path.join(REPO, 'skills'), '/work/': WORK };
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const pre = Object.keys(ROOTS).find(p => u.startsWith(p));
  const f = pre ? path.join(ROOTS[pre], u.slice(pre.length)) : null;
  if (!f || !f.startsWith(ROOTS[pre])) { res.writeHead(404); return res.end(); }
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' }); res.end(d); });
}).listen(0);

function ffmpeg(out) {
  return spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', process.env.X264_PRESET || 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30', '-g', '60', out], { stdio: ['pipe', 'inherit', 'inherit'] });
}
const write = (ff, buf) => ff.stdin.write(buf) ? null : new Promise(r => ff.stdin.once('drain', r));

(async () => {
  const browser = await chromium.launch({ ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}) });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => { errors.push(e.message); console.log('[pageerror]', e.message); });
  page.on('console', m => { if (m.type() === 'error') { errors.push(m.text()); console.log('[page]', m.text()); } });
  await page.goto(`http://localhost:${server.address().port}/engine/index.html`);
  await page.waitForFunction(() => window.STUDIO && window.STUDIO.ready);
  await page.evaluate(() => window.STUDIO.ready);
  const n = await page.evaluate(() => window.LESSON.scenes.length);
  const ids = which === 'all' ? [...Array(n).keys()] : which.split(',').map(Number);
  fs.mkdirSync(path.join(WORK, 'scenes'), { recursive: true });
  for (const id of ids) {
    const tag = 's' + String(id).padStart(2, '0');
    const info = await page.evaluate(i => window.STUDIO.load(i), id);
    if (flag === '--stills') {
      for (const t of flagVal.split(',').map(Number)) {
        await page.evaluate(f => window.STUDIO.frame(f), Math.round(t * 30));
        await page.screenshot({ path: path.join(WORK, 'scenes', `${tag}_t${t.toFixed(1)}.jpg`), type: 'jpeg', quality: 90 });
      }
      continue;
    }
    const dirty = f => { const a = (f - 1) / 30, b = f / 30; return f === 0 || info.iv.some(([s, e]) => s <= b + 1e-6 && e >= a - 1e-6); };
    const tmp = path.join(WORK, 'scenes', tag + '.part.mp4'), fin = path.join(WORK, 'scenes', tag + '.mp4');
    const ff = ffmpeg(tmp), done = new Promise(r => ff.on('close', r));
    let last = null, captured = 0; const qcAt = Math.max(0, info.frames - Math.round(.6 * 30)); let qc = [];
    const T0 = Date.now();
    for (let f = 0; f < info.frames; f++) {
      if (!last || dirty(f) || f === qcAt) {
        await page.evaluate(f => window.STUDIO.frame(f), f);
        last = await page.screenshot({ type: 'jpeg', quality: 92 }); captured++;
        if (f === qcAt) qc = await page.evaluate(() => window.STUDIO.qc());
      }
      const w = write(ff, last); if (w) await w;
    }
    ff.stdin.end(); const code = await done;
    if (code !== 0) { console.log('ffmpeg failed for', tag); process.exitCode = 1; continue; }
    fs.renameSync(tmp, fin);
    fs.writeFileSync(path.join(WORK, 'scenes', tag + '.qc.json'), JSON.stringify({ frames: info.frames, captured, layout: qc, errors, ms: Date.now() - T0 }, null, 1));
    console.log(`${tag}: ${info.frames} frames, ${captured} captured, ${((Date.now() - T0) / 1000).toFixed(1)} s`);
  }
  await browser.close(); server.close();
})().catch(e => { console.error(e); process.exit(1); });
