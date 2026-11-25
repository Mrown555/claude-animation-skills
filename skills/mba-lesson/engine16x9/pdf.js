// HTML -> PDF (A4) and HTML -> PNG with the same Playwright Chromium the renderer uses.
//   node pdf.js <in.html> <out.pdf>        node pdf.js --png <in.html> <out.png> <width> <height>
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const a = process.argv.slice(2);
  const png = a[0] === '--png'; if (png) a.shift();
  const browser = await chromium.launch({ ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}) });
  const page = await browser.newPage(png ? { viewport: { width: +a[2], height: +a[3] } } : {});
  await page.goto('file://' + path.resolve(a[0]), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  if (png) await page.screenshot({ path: a[1], fullPage: true, type: a[1].endsWith('.jpg') ? 'jpeg' : 'png', ...(a[1].endsWith('.jpg') ? { quality: 85 } : {}) });
  else await page.pdf({ path: a[1], format: 'A4', printBackground: true, margin: { top: '16mm', bottom: '16mm', left: '15mm', right: '15mm' },
    displayHeaderFooter: true, headerTemplate: '<span></span>', footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#888"><span class="pageNumber"></span> / <span class="totalPages"></span></div>' });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
