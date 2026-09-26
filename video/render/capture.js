// Render every frame of index.html by calling window.render(t), save JPEGs to /out/frames.
// Usage (inside the puppeteer image): node capture.js [startFrame] [endFrame]
const puppeteer = require('puppeteer');
const fs = require('fs');
(async () => {
  const tl = JSON.parse(fs.readFileSync('/work/timeline.json', 'utf8'));
  const n = Math.ceil(tl.total * tl.fps);
  const a = +(process.argv[2] || 0), b = Math.min(+(process.argv[3] || n), n);
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--font-render-hinting=none'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto('file:///work/index.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  if (process.env.NOCAP) await page.addStyleTag({ content: '#cap { display:none !important }' });
  fs.mkdirSync('/out/frames', { recursive: true });
  const list = process.env.FRAMES ? process.env.FRAMES.split(',').map(Number) : null;
  for (let i = a; i < b; i++) {
    if (list && !list.includes(i)) continue;
    await page.evaluate(t => window.render(t), i / tl.fps);
    await page.screenshot({ path: `/out/frames/f${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 92 });
    if (i % 300 === 0) console.log('frame', i, '/', n);
  }
  await browser.close();
  console.log('done', a, b);
})();
