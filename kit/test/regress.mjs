// regress.mjs -- does the kit's engine still draw a film exactly as the film's own frozen copy does? Run it after any
// change to the kit's engine: every film made so far must render frame-identical with the new one (or you know which
// frames moved, and why).
//
//   node test/regress.mjs <film folder> [--every 1] [--from 0 --to N] [--sheet 12] [--out dir] [--self] [--swap a.js,b.js]
//   (--self: the film against itself = the render-noise floor; --swap: only these files, for bisecting;
//    --only-engine: don't swap the kit's vocab/ files)
//
// Serves the film twice, from its own folder, read-only: BASELINE = the film exactly as it is; CANDIDATE = the same
// film with the kit's web/lib/engine.js, kit.js and shaft.js, plus every file in the kit's vocab/ folder (if it has
// one) that the film also has in web/lib/, swapped in by the server. Two pages render every frame (or every Nth) and
// hash the full 1920x1080 pixels. Identical hashes = identical frames. A mismatch saves both PNGs. Nothing is written
// into the film.
// --sheet K also saves K evenly spaced candidate frames; test/sheet.py puts them beside the film's master for a look.
// Writes <out>/report.json (default out: the kit's test/out/<film>/).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { launch } from '../template/render/browser.mjs';

const KIT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : d; };
const film = path.resolve(args[0] && !args[0].startsWith('--') ? args[0] : '.');
const name = path.basename(film);
const out = path.resolve(opt('out', path.join(KIT, 'test', 'out', name)));
fs.mkdirSync(out, { recursive: true });
const FPS = 24;
const timing = JSON.parse(fs.readFileSync(path.join(film, 'song', 'timing.json'), 'utf8'));
const total = Math.ceil(timing.duration * FPS);
const every = +opt('every', 1), f0 = +opt('from', 0), f1 = Math.min(total, +opt('to', total));
const nSheet = +opt('sheet', 12);
// the film's own render API, read from its renderer: window.DT_ready / DT_renderFrame / DT_fatal and canvas#gl in
// films made from this kit; an older engine may use another prefix (XX_renderFrame) and the page's only <canvas>
const rsrc = fs.readFileSync(path.join(film, 'render', 'render.mjs'), 'utf8');
const API = (/window\.([A-Z]+)_renderFrame/.exec(rsrc) || [0, 'DT'])[1];
const CANVAS = /getElementById\('gl'\)/.test(rsrc) ? "document.getElementById('gl')" : "document.querySelector('canvas')";

// ---- the swap: URL path -> kit file
const over = {};
const only = opt('swap') ? String(opt('swap')).split(',') : null;   // --swap engine.js,kit.js: swap just these (bisecting)
if (!opt('self')) for (const f of ['engine.js', 'kit.js', 'shaft.js']) if (!only || only.includes(f)) over[`/web/lib/${f}`] = path.join(KIT, 'template', 'web', 'lib', f);
if (!opt('only-engine') && !opt('self') && fs.existsSync(path.join(KIT, 'vocab'))) {
  for (const f of fs.readdirSync(path.join(KIT, 'vocab'))) {
    if (fs.existsSync(path.join(film, 'web', 'lib', f)) && (!only || only.includes(f))) over[`/web/lib/${f}`] = path.join(KIT, 'vocab', f);
  }
}

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json',
  '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.ttf': 'font/ttf',
  '.otf': 'font/otf', '.woff': 'font/woff', '.woff2': 'font/woff2', '.m4a': 'audio/mp4', '.mp3': 'audio/mpeg', '.wav': 'audio/wav' };
function server(swap) {
  const s = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    // /film.js is film.json as window.DT_FILM, generated the way render/serve.mjs does it (a film made from this kit
    // has no such file on disk, and its strict page refuses to start without it)
    if (p === '/film.js' && !fs.existsSync(path.join(film, 'film.js'))) {
      return fs.readFile(path.join(film, 'film.json'), 'utf8', (err, txt) => {
        if (err) { res.writeHead(404); return res.end('not found'); }
        res.writeHead(200, { 'Content-Type': 'text/javascript; charset=utf-8', 'Cache-Control': 'no-cache' });
        res.end('window.DT_FILM = ' + txt + ';\n');
      });
    }
    if (p.endsWith('/')) p += 'index.html';
    let file = swap && over[p] ? over[p] : path.join(film, p);
    if (!(swap && over[p]) && !path.resolve(file).startsWith(film)) { res.writeHead(403); return res.end(); }
    fs.readFile(file, (err, buf) => {
      if (err) { res.writeHead(404); return res.end('not found'); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
      res.end(buf);
    });
  });
  return new Promise((r) => s.listen(0, '127.0.0.1', () => r(s)));
}

const HASH = `(() => {
  const src = ${CANVAS};
  let cv = window.__rgCv;
  if (!cv) { cv = window.__rgCv = document.createElement('canvas'); cv.width = src.width; cv.height = src.height; }
  const g = cv.getContext('2d', { willReadFrequently: true });
  g.drawImage(src, 0, 0);
  const u = new Uint32Array(g.getImageData(0, 0, cv.width, cv.height).data.buffer);
  let h1 = 0x811c9dc5 | 0, h2 = 0;
  for (let i = 0; i < u.length; i++) { h1 = Math.imul(h1 ^ u[i], 16777619); h2 = (h2 + Math.imul(u[i], i + 1)) | 0; }
  return (h1 >>> 0).toString(16) + ':' + (h2 >>> 0).toString(16);
})()`;

// 16x16-tile channel means of the frame HASH just read (0..255). Two pages of the SAME film differ by render noise: at
// most 1/255 on up to ~150 pixels, and once 10/255 on 12 corner pixels (a film against itself), which moves a tile mean
// by < 0.5. A frame counts as DIFFERENT only when some tile mean moves by more than NOISE_TILE.
const NOISE_TILE = 1.0;
const SIG = `(() => {
  const cv = window.__rgCv, w = cv.width, h = cv.height, T = 16, tw = Math.ceil(w / T), th = Math.ceil(h / T);
  const d = cv.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, w, h).data;
  const sum = new Float64Array(tw * th * 3), cnt = new Float64Array(tw * th);
  for (let y = 0; y < h; y++) {
    const ty = (y / T) | 0;
    for (let x = 0; x < w; x++) {
      const k = (ty * tw + ((x / T) | 0)), i = (y * w + x) * 4;
      sum[k * 3] += d[i]; sum[k * 3 + 1] += d[i + 1]; sum[k * 3 + 2] += d[i + 2]; cnt[k]++;
    }
  }
  return Array.from(sum, (v, i) => v / cnt[(i / 3) | 0]);
})()`;

async function open(browser, port, label) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', (r) => { if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${decodeURIComponent(new URL(r.url()).pathname)}`); });
  page.on('requestfailed', (r) => errors.push(`FAILED ${decodeURIComponent(new URL(r.url()).pathname)} ${r.failure() && r.failure().errorText}`));
  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto(`http://127.0.0.1:${port}/web/index.html?mode=render&strict=1`);
  try { await page.waitForFunction(`window.${API}_ready === true`, { timeout: 180000 }); }
  catch (e) { throw new Error(`${label} page never became ready (3 min): ${errors.slice(-8).join(' | ') || 'no errors logged'}`); }
  const fatal = await page.evaluate((api) => window[api + '_fatal'] || null, API);
  if (fatal) throw new Error(`${label} page not healthy: ${fatal}\n${errors.slice(-5).join('\n')}`);
  return { page, errors };
}

async function frame(p, n) {
  await p.page.evaluate(([api, k]) => window[api + '_renderFrame'](k), [API, n]);
  return p.page.evaluate(HASH);
}
async function png(p, file, w = 1920) {
  const data = await p.page.evaluate(([w, sel]) => {
    const src = sel === 'gl' ? document.getElementById('gl') : document.querySelector('canvas');
    if (w === src.width) return src.toDataURL('image/png');
    const cv = document.createElement('canvas'); cv.width = w; cv.height = Math.round(w * 9 / 16);
    cv.getContext('2d').drawImage(src, 0, 0, cv.width, cv.height);
    return cv.toDataURL('image/png');
  }, [w, CANVAS.includes("'gl'") ? 'gl' : 'canvas']);
  fs.writeFileSync(file, Buffer.from(data.slice(data.indexOf(',') + 1), 'base64'));
}

const sa = await server(false), sb = await server(true);
const browser = await launch();
const t0 = Date.now();
const report = { film, name, frames: [f0, f1], every, overrides: Object.fromEntries(Object.entries(over).map(([k, v]) => [k, path.relative(KIT, v)])),
  checked: 0, identical: 0, noise: 0, noiseMax: 0, mismatches: [], sheet: [] };
try {
  const A = await open(browser, sa.address().port, 'baseline');
  const B = await open(browser, sb.address().port, 'candidate');
  const list = [];
  for (let f = f0; f < f1; f += every) list.push(f);
  const sheetAt = new Set(Array.from({ length: nSheet }, (_, i) => list[Math.floor((i + 0.5) * list.length / nSheet)]));
  for (const f of list) {
    const [ha, hb] = await Promise.all([frame(A, f), frame(B, f)]);
    report.checked++;
    if (ha === hb) report.identical++;
    else {
      const [ga, gb] = await Promise.all([A.page.evaluate(SIG), B.page.evaluate(SIG)]);
      let dmax = 0, over = 0;
      for (let i = 0; i < ga.length; i++) { const d = Math.abs(ga[i] - gb[i]); if (d > dmax) dmax = d; if (d > NOISE_TILE) over++; }
      if (dmax <= NOISE_TILE) { report.noise++; report.noiseMax = Math.max(report.noiseMax, +dmax.toFixed(3)); }
      else {
        report.mismatches.push({ f, t: +(f / FPS).toFixed(3), tileMax: +dmax.toFixed(2), tilesOver: over });
        if (report.mismatches.length <= 40) {
          await png(A, path.join(out, `f${String(f).padStart(5, '0')}_base.png`));
          await png(B, path.join(out, `f${String(f).padStart(5, '0')}_kit.png`));
        }
      }
    }
    if (sheetAt.has(f)) { const fn = `sheet_${String(f).padStart(5, '0')}.png`; await png(B, path.join(out, fn), 640); report.sheet.push({ f, file: fn }); }
    if (report.checked % 200 === 0) {
      const el = (Date.now() - t0) / 1000;
      console.log(`${name}: ${report.checked}/${list.length} frames, ${report.noise} noise, ${report.mismatches.length} DIFFERENT, ${(report.checked / el).toFixed(1)} fps`);
    }
  }
  report.pageErrors = { baseline: A.errors.slice(0, 10), candidate: B.errors.slice(0, 10) };
} finally {
  report.seconds = Math.round((Date.now() - t0) / 1000);
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
  await browser.close().catch(() => {});
  sa.close(); sb.close();
}
console.log(`${name}: ${report.checked} frames: ${report.identical} identical, ${report.noise} within render noise (tile max ${report.noiseMax}), ${report.mismatches.length} DIFFERENT (${report.seconds} s) -> ${path.join(out, 'report.json')}`);
if (report.mismatches.length) console.log('first differing frames:', report.mismatches.slice(0, 12).map((m) => m.f).join(' '));
process.exit(report.mismatches.length ? 1 : 0);
