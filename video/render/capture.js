// Render frames of index.html by calling window.render(t), saving JPEGs to /out/frames.
// Usage (inside the puppeteer image): node capture.js [startFrame] [endFrame]
// Env: FRAMES=264,1500 renders only those frames; NOCAP=1 hides the captions.
const puppeteer = require('puppeteer');
const fs = require('fs');
(async () => {
  const tl = JSON.parse(fs.readFileSync('/work/timeline.json', 'utf8'));
  const n = Math.ceil(tl.total * tl.fps);
  const start = +(process.argv[2] || 0), end = Math.min(+(process.argv[3] || n), n);
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--font-render-hinting=none'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto('file:///work/index.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  if (process.env.NOCAP) await page.addStyleTag({ content: '#cap { display:none !important }' });
  fs.mkdirSync('/out/frames', { recursive: true });
  const only = process.env.FRAMES ? new Set(process.env.FRAMES.split(',').map(Number)) : null;
  for (let i = start; i < end; i++) {
    if (only && !only.has(i)) continue;
    await page.evaluate(t => window.render(t), i / tl.fps);
    await page.screenshot({ path: `/out/frames/f${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 92 });
    if (i % 300 === 0) console.log('frame', i, '/', n);
  }
  await browser.close();
  console.log('done', start, end);
})();
