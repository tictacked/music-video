// check_assets.mjs: walk every frame of a range and report UNDECLARED assets (info.missing) + page errors,
// which --loose previews hide and the strict final render would die on. Uses a render slot.
//   node render/check_assets.mjs F0 F1        (frame indices: frame = round(seconds * 24))
import fs from 'node:fs';
import path from 'node:path';
import { serve, ROOT } from './serve.mjs';
import { launch } from './browser.mjs';
const [f0, f1] = [+process.argv[2], +process.argv[3]];
const lockDir = path.join(ROOT, 'notes', '.render-slots');
fs.mkdirSync(lockDir, { recursive: true });   // a fresh film has no slot folder yet: without it the wait below never ends
let mySlot = null;
while (!mySlot) {
  for (let i = 0; i < 2 && !mySlot; i++) { const p = path.join(lockDir, `slot${i}.lock`); try { fs.writeFileSync(p, String(process.pid), { flag: 'wx' }); mySlot = p; } catch {} }
  if (!mySlot) await new Promise((r) => setTimeout(r, 1000));
}
const release = () => { try { fs.unlinkSync(mySlot); } catch {} };
process.on('exit', release);
const server = await serve(0);
const browser = await launch();
const page = await browser.newPage();
const errors = [];
page.on('console', (m) => { const t = m.text(); if ((m.type() === 'error' || m.type() === 'warn') && !/404|not found \(yet\)|PROBLEMS|willReadFrequently/.test(t)) errors.push(t); });
page.on('pageerror', (e) => errors.push('[pageerror] ' + e.message));
await page.setViewport({ width: 1920, height: 1080 });
await page.goto(`http://127.0.0.1:${server.address().port}/web/index.html?mode=render`);
await page.waitForFunction('window.DT_ready === true', { timeout: 90000 });
const miss = new Map();
for (let f = f0; f <= f1; f++) {
  const info = await page.evaluate((n) => window.DT_renderFrame(n), f);
  if (info.missing) for (const k of info.missing.split(', ')) miss.set(k, (miss.get(k) || []).concat(f));
}
console.log('frames', f0, '-', f1, 'undeclared:', miss.size ? [...miss].map(([k, fs]) => `${k} @ ${fs.slice(0, 5).join(',')}${fs.length > 5 ? '...' : ''}`).join('\n  ') : 'none');
console.log('page messages:', errors.length ? '\n' + [...new Set(errors)].slice(0, 20).join('\n') : 'none');
await browser.close(); server.close(); release(); process.exit(0);
