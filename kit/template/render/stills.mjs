// Render stills (and a contact sheet) so a Claude can SEE the video without watching it.
//
//   node render/stills.mjs --times 12.5,40,61.2            frames at song times (timeline mode)
//   node render/stills.mjs --shots v1_wide,c1_flip --n 4   N frames spread across each named shot
//   node render/stills.mjs --all --every 4                 one frame every 4 s of the whole song
//   node render/stills.mjs --scene street --dur 8 --n 6 [--at 22.8] [--params '{"k":1}']   sandbox: one scene alone
//   node render/stills.mjs --scene title_card --frames 0,1,2,3   exact frame indices (sandbox or timeline)
//   node render/stills.mjs --trtest shatter --frames 36,48,60     a transition alone (trA -> trB at 2.0 s; --trdur 1)
// options: --out <dir> (default notes/stills/<stamp>)  --w 960 (still width)  --sheet (also write sheet.png)
//          --cols 3  --label (each still's time, frame and shot on the sheet)  --keep-going (skip a frame that throws)
// Prints the paths it wrote. Exit code 1 with the page error if the scene throws.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { serve, ROOT } from './serve.mjs';
import { launch } from './browser.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : d; };
const FPS = 24;
const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);   // 15 kept a trailing '.': a folder Windows can't list
const outDir = path.resolve(opt('out', path.join(ROOT, 'notes', 'stills', stamp)));
fs.mkdirSync(outDir, { recursive: true });
const stillW = +opt('w', 960);

// ---- GPU slot lock: the director and the painters share one GPU (and whatever else is using it).
// Each headless render costs ~0.8 GB of VRAM, so at most SLOTS renders run at once; others wait.
const SLOTS = 2;   // the video model can hold most of the memory while clips are being made
const lockDir = path.join(ROOT, 'notes', '.render-slots');
fs.mkdirSync(lockDir, { recursive: true });
let mySlot = null;
const release = () => { if (mySlot) { try { fs.unlinkSync(mySlot); } catch {} mySlot = null; } };
process.on('exit', release);
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => { release(); process.exit(130); });
for (let waited = 0; !mySlot; waited++) {
  for (let i = 0; i < SLOTS && !mySlot; i++) {
    const p = path.join(lockDir, `slot${i}.lock`);
    try {
      const st = fs.statSync(p);
      if (Date.now() - st.mtimeMs > 6 * 60 * 1000) fs.unlinkSync(p);   // stale (a crashed run): reclaim
    } catch {}
    try { fs.writeFileSync(p, String(process.pid), { flag: 'wx' }); mySlot = p; } catch {}
  }
  if (!mySlot) {
    if (waited === 0) console.log('waiting for a GPU render slot (other painters are rendering)...');
    await new Promise((r) => setTimeout(r, 1000));
  }
}

const server = await serve(0);
const port = server.address().port;
const q = new URLSearchParams({ mode: 'render' });
if (opt('view')) q.set('view', opt('view'));   // --view <name>: passed to the page as ?view= (for a film's own debug views)
if (opt('trtest')) { q.set('trtest', opt('trtest')); if (opt('trdur')) q.set('trdur', opt('trdur')); }   // --trtest jigsaw [--trdur 1]
if (opt('scene')) {
  q.set('scene', opt('scene')); q.set('dur', opt('dur', '8')); q.set('at', opt('at', '0'));
  if (opt('params')) q.set('params', opt('params'));
}
// A headless Chrome can hang forever in browser.close() (a finished render once kept its slot lock fresh via the
// heartbeat and blocked the crew's only slot). Close with a deadline, then kill the process.
async function closeBrowser(b) {
  if (!b) return;
  const proc = b.process();
  await Promise.race([b.close().catch(() => {}), new Promise((r) => setTimeout(r, 8000))]);
  try { if (proc && proc.exitCode == null) proc.kill('SIGKILL'); } catch {}
}
const browser = await launch();
const page = await browser.newPage();
const errors = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warn') errors.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', (e) => errors.push('[pageerror] ' + e.message));
await page.setViewport({ width: 1920, height: 1080 });
await page.goto(`http://127.0.0.1:${port}/web/index.html?${q}`);
try {
  await page.waitForFunction('window.DT_ready === true', { timeout: 90000 });
} catch (e) {
  console.error('page never became ready:\n' + errors.join('\n'));
  await closeBrowser(browser); server.close(); process.exit(1);
}

// which frames?
const shots = await page.evaluate(() => DT.shots.map((s) => ({ id: s.id, scene: s.scene, start: s.start, end: s.end })));
let frames = [];
if (opt('frames')) frames = String(opt('frames')).split(',').map(Number);
else if (opt('times')) frames = String(opt('times')).split(',').map((t) => Math.round(+t * FPS));
else if (opt('scene')) {
  const at = +opt('at', 0), dur = +opt('dur', 8), n = +opt('n', 6);
  for (let i = 0; i < n; i++) frames.push(Math.round((at + dur * (i + 0.5) / n) * FPS));
} else if (opt('shots')) {
  const want = String(opt('shots')).split(','), n = +opt('n', 3);
  for (const id of want) {
    const s = shots.find((x) => x.id === id);
    if (!s) { console.error('no shot ' + id + '. shots: ' + shots.map((x) => x.id).join(', ')); continue; }
    for (let i = 0; i < n; i++) frames.push(Math.round((s.start + (s.end - s.start) * (i + 0.5) / n) * FPS));
  }
} else if (opt('all')) {
  const every = +opt('every', 4), dur = await page.evaluate(() => DT.timing.duration);
  for (let t = every / 2; t < dur; t += every) frames.push(Math.round(t * FPS));
}
if (!frames.length) { console.error('nothing to render (use --times, --shots, --all, --scene or --frames)'); await closeBrowser(browser); server.close(); process.exit(1); }

const written = [];
for (const f of frames) {
  let info;
  const t0 = Date.now();
  try { info = await page.evaluate((n) => window.DT_renderFrame(n), f); }
  catch (e) {
    console.error(`frame ${f} failed: ${e.message}\n` + errors.slice(-3).join('\n'));
    if (opt('keep-going')) continue;   // director's reviews: one reel mid-edit must not stop the whole-film sheet
    await closeBrowser(browser); server.close(); process.exit(1);
  }
  const ms = Date.now() - t0;
  // --label: the time, frame and shot id drawn in the page onto a SHEET-ONLY copy (the still itself stays clean)
  const label = opt('label') ? `${(f / FPS).toFixed(2)}s  f${f}  ${info.shot}${info.transition ? ' +' + info.transition : ''}` : null;
  const [data, ldata] = await page.evaluate((w, label) => {
    const src = document.getElementById('gl');
    const c = document.createElement('canvas'); c.width = w; c.height = Math.round(w * 9 / 16);
    const g = c.getContext('2d');
    g.drawImage(src, 0, 0, c.width, c.height);
    const clean = c.toDataURL('image/png');
    if (!label) return [clean, null];
    const s = Math.max(12, Math.round(w / 36));
    g.font = `bold ${s}px "Space Mono", monospace`;
    g.fillStyle = 'rgba(0,0,0,0.62)'; g.fillRect(0, 0, g.measureText(label).width + s, s * 1.7);
    g.fillStyle = '#ffffff'; g.textBaseline = 'middle'; g.fillText(label, s / 2, s * 0.85);
    return [clean, c.toDataURL('image/png')];
  }, stillW, label);
  const name = `f${String(f).padStart(5, '0')}_${(f / FPS).toFixed(2)}s_${info.shot}.png`.replace(/[^\w.\-]/g, '_');
  const p = path.join(outDir, name);
  fs.writeFileSync(p, Buffer.from(data.split(',')[1], 'base64'));
  let lp = null;
  if (ldata) { lp = path.join(outDir, '_label_' + name); fs.writeFileSync(lp, Buffer.from(ldata.split(',')[1], 'base64')); }
  written.push({ p, lp, info, ms });
  console.log(`${p}   (${info.shot}${info.transition ? ' +' + info.transition : ''}, ${ms} ms)`);
}
if (errors.length) console.log('page messages:\n' + errors.slice(0, 20).join('\n'));

if (opt('sheet') || written.length > 1) {
  // contact sheet via ffmpeg tile (with --label, the labelled copies; they're deleted afterwards)
  const cols = +opt('cols', Math.min(3, written.length)), rows = Math.ceil(written.length / cols);
  const list = path.join(outDir, 'sheet_inputs.txt');
  fs.writeFileSync(list, written.map((w) => `file '${(w.lp || w.p).replace(/\\/g, '/')}'`).join('\n'));
  const sheet = path.join(outDir, 'sheet.png');
  const vf = [`scale=${Math.round(stillW / 2)}:-1`, `tile=${cols}x${rows}:padding=4:color=black`];
  try {
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-vf', vf.join(','), '-frames:v', '1', sheet], { cwd: ROOT });
    console.log('sheet: ' + sheet);
  } catch (e) { console.error('sheet failed: ' + e.message); }
  for (const w of written) if (w.lp) { try { fs.unlinkSync(w.lp); } catch {} }
}
await closeBrowser(browser);
server.close();
