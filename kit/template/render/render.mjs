// The final renderer: every frame of the song, deterministic, chunked, resumable, parallel.
//
//   node render/render.mjs                        full 1080p render -> out/<film.json name>.mp4
//   node render/render.mjs --preview              960x540, faster, -> out/preview.mp4
//   node render/render.mjs --from 140 --to 170    only that stretch (seconds) -> out/range_140-170.mp4
//   options: --workers 2 (browsers; each holds a GPU slot)  --chunk 240 (frames per chunk)  --crf 15  --fresh (discard chunks)  --loose (no strict checks: previews)
//
// Each chunk = N consecutive frames piped as PNGs into one ffmpeg (x264) -> out/chunks-<tag>/cNNNN.mp4.
// A finished chunk is never re-rendered (delete it or pass --fresh to redo). The final step concatenates
// the chunks (stream copy) and muxes the song. Frames are pure functions of their index, so chunks can
// be rendered in any order by any worker and still join seamlessly.
import fs from 'node:fs';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { serve, ROOT } from './serve.mjs';
import { FILM } from './film.mjs';
import { launch } from './browser.mjs';

const args = process.argv.slice(2);
// --help, or any flag this script doesn't know, prints the usage instead of starting a render (a typo used to launch
// a full-length render)
const KNOWN = ['preview', 'from', 'to', 'workers', 'chunk', 'crf', 'fresh', 'loose'];
const unknown = args.filter((a) => a.startsWith('-') && !KNOWN.includes(a.replace(/^--/, '')));
if (unknown.length) {
  const head = fs.readFileSync(new URL(import.meta.url), 'utf8').split('\n').filter((l) => l.startsWith('//')).slice(0, 11);
  console.log(head.map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
  if (!unknown.every((a) => a === '--help' || a === '-h')) console.log(`\nunknown option(s): ${unknown.join(' ')}`);
  process.exit(unknown.every((a) => a === '--help' || a === '-h') ? 0 : 1);
}
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : d; };
const FPS = 24;
const preview = !!opt('preview');
const W = preview ? 960 : 1920, H = preview ? 540 : 1080;
const workers = +opt('workers', 2);
const chunk = +opt('chunk', 240);
const crf = +opt('crf', preview ? 20 : 15);
const timing = JSON.parse(fs.readFileSync(path.join(ROOT, 'song', 'timing.json'), 'utf8'));
const total = Math.ceil(timing.duration * FPS);
// bar anchors (--from B7 --to B16) and --to END. B<n> is the film's bar anchor, beat0 + (4n + barOffset) beats, the
// same formula web/timeline.js uses.
const at = (v) => (String(v).toUpperCase() === 'END' ? timing.duration
  : /^B[\d.]+$/i.test(String(v)) ? timing.beat0 + (4 * parseFloat(String(v).slice(1)) + (timing.barOffset || 0)) * 60 / timing.bpm : +v);
const f0 = opt('from') ? Math.round(at(opt('from')) * FPS) : 0;   // round, like shot starts (--from B7 starts on the shot's own first frame)
const f1 = opt('to') ? Math.min(total, Math.ceil(at(opt('to')) * FPS)) : total;
const tag = (preview ? 'preview' : 'full') + (opt('from') || opt('to') ? `_${opt('from', 0)}-${opt('to', 'end')}` : '');
const outDir = path.join(ROOT, 'out');
const chunkDir = path.join(outDir, 'chunks-' + tag);
if (opt('fresh')) fs.rmSync(chunkDir, { recursive: true, force: true });
fs.mkdirSync(chunkDir, { recursive: true });

// A headless Chrome can hang forever in browser.close() (a finished render once kept its slot lock fresh via the
// heartbeat and blocked the crew's only slot). Close with a deadline, then kill the process.
async function closeBrowser(b) {
  if (!b) return;
  const proc = b.process();
  await Promise.race([b.close().catch(() => {}), new Promise((r) => setTimeout(r, 8000))]);
  try { if (proc && proc.exitCode == null) proc.kill('SIGKILL'); } catch {}
}

// ---- GPU slots (shared with render/stills.mjs): hold one per worker, heartbeat so they never look stale
const lockDir = path.join(ROOT, 'notes', '.render-slots');
fs.mkdirSync(lockDir, { recursive: true });
const held = [];
async function acquire() {
  for (let waited = 0; ; waited++) {
    for (let i = 0; i < 2; i++) {   // the same 2 slots as stills.mjs (a third one here starved the painters' stills)
      const p = path.join(lockDir, `slot${i}.lock`);
      try { if (Date.now() - fs.statSync(p).mtimeMs > 6 * 60 * 1000) fs.unlinkSync(p); } catch {}
      try { fs.writeFileSync(p, 'render ' + process.pid, { flag: 'wx' }); held.push(p); return p; } catch {}
    }
    if (waited === 0) console.log('waiting for a GPU slot...');
    await new Promise((r) => setTimeout(r, 1000));
  }
}
const beat = setInterval(() => { const now = new Date(); for (const p of held) { try { fs.utimesSync(p, now, now); } catch {} } }, 30000);
const releaseAll = () => { for (const p of held.splice(0)) { try { fs.unlinkSync(p); } catch {} } };
process.on('exit', releaseAll);
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => { releaseAll(); process.exit(130); });

// ---- the work queue
const chunks = [];
for (let s = f0, i = Math.floor(f0 / chunk); s < f1; i++) {
  const a = Math.max(f0, i * chunk), b = Math.min(f1, (i + 1) * chunk);
  chunks.push({ i, a, b, file: path.join(chunkDir, `c${String(i).padStart(4, '0')}.mp4`) });
  s = b;
}
// A PREVIEW chunk older than the newest web/ or manifest file is stale, so it is redone. The full render keeps
// finished chunks; delete a chunk by hand to redo it.
function newestMtime(...roots) {
  let m = 0;
  const walk = (p) => { let st; try { st = fs.statSync(p); } catch { return; }
    if (st.isDirectory()) for (const f of fs.readdirSync(p)) walk(path.join(p, f)); else m = Math.max(m, st.mtimeMs); };
  for (const r of roots) walk(path.join(ROOT, r));
  return m;
}
const stamp = preview ? newestMtime('web', 'assets/manifest.js') : 0;
const todo = chunks.filter((c) => !fs.existsSync(c.file) || (preview && fs.statSync(c.file).mtimeMs < stamp));
console.log(`${tag}: frames ${f0}-${f1} (${((f1 - f0) / FPS).toFixed(1)} s) in ${chunks.length} chunks, ${todo.length} to render, ${workers} workers, ${W}x${H} crf ${crf}`);

const server = await serve(0);
const port = server.address().port;
const t0 = Date.now();
let framesDone = 0;

async function worker(id) {
  await acquire();
  const browser = await launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.setViewport({ width: 1920, height: 1080 });
  // strict: a script that failed to load (e.g. a transient ERR_NO_BUFFER_SPACE) must never become a silent
  // placeholder in the final film. Retry the page a few times, then give up loudly.
  for (let attempt = 1; ; attempt++) {
    // strict by default (the final film must never contain a placeholder); --loose for previews while scenes are missing
    await page.goto(`http://127.0.0.1:${port}/web/index.html?mode=render${opt('loose') ? '' : '&strict=1'}`);
    await page.waitForFunction('window.DT_ready === true', { timeout: 120000 });
    const fatal = await page.evaluate(() => window.DT_fatal || null);
    if (!fatal) break;
    console.error(`[w${id}] page not healthy (attempt ${attempt}): ${fatal}`);
    if (attempt >= 4) throw new Error('page failed strict checks: ' + fatal);
    await new Promise((r) => setTimeout(r, 1500 * attempt));
  }
  while (todo.length) {
    const c = todo.shift();
    const part = c.file.replace(/\.mp4$/, '.part.mp4');
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-preset', preview ? 'veryfast' : 'slow', '-crf', String(crf), '-pix_fmt', 'yuv420p', '-tune', 'film',
      '-g', String(FPS * 2), '-r', String(FPS), part], { stdio: ['pipe', 'inherit', 'inherit'] });
    const ffDone = new Promise((res, rej) => ff.on('close', (code) => (code === 0 ? res() : rej(new Error('ffmpeg exit ' + code)))));
    const tc = Date.now();
    for (let f = c.a; f < c.b; f++) {
      let data;
      try {
        await page.evaluate((n) => window.DT_renderFrame(n), f);
        data = await page.evaluate((w) => {
          const src = document.getElementById('gl');
          if (w === src.width) return src.toDataURL('image/png');
          const cv = document.createElement('canvas'); cv.width = w; cv.height = Math.round(w * 9 / 16);
          cv.getContext('2d').drawImage(src, 0, 0, cv.width, cv.height);
          return cv.toDataURL('image/png');
        }, W);
      } catch (e) {
        console.error(`[w${id}] frame ${f} failed: ${e.message}\n${errors.slice(-5).join('\n')}`);
        ff.stdin.end(); await ffDone.catch(() => {}); try { fs.unlinkSync(part); } catch {}
        throw e;
      }
      const buf = Buffer.from(data.slice(data.indexOf(',') + 1), 'base64');
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      framesDone++;
    }
    ff.stdin.end();
    await ffDone;
    fs.renameSync(part, c.file);
    const el = (Date.now() - t0) / 1000, rate = framesDone / el;
    const left = todo.length * chunk / Math.max(rate, 0.01);
    console.log(`[w${id}] chunk ${c.i} (${(c.a / FPS).toFixed(1)}-${(c.b / FPS).toFixed(1)} s) ${((Date.now() - tc) / (c.b - c.a)).toFixed(0)} ms/frame   total ${rate.toFixed(1)} fps, ~${(left / 60).toFixed(1)} min left`);
  }
  await closeBrowser(browser);
}

try {
  // nothing left to render (a re-mux): no browser, no GPU
  if (todo.length) await Promise.all(Array.from({ length: Math.min(workers, todo.length) }, (_, i) => worker(i)));
} finally {
  clearInterval(beat);
  releaseAll();
  server.close();
}

// ---- join + mux
const list = path.join(chunkDir, 'list.txt');
fs.writeFileSync(list, chunks.map((c) => `file '${c.file.replace(/\\/g, '/')}'`).join('\n'));
const name = tag === 'full' ? `${FILM.name}.mp4` : tag === 'preview' ? 'preview.mp4' : `range_${tag}.mp4`;
const out = path.join(outDir, name);
const ss = f0 / FPS, dur = (f1 - f0) / FPS;
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list,
  '-ss', String(ss), '-t', String(dur), '-i', path.join(ROOT, FILM.audio || 'song/audio.m4a'),   // film.json audio (e.g. song/audio_final.m4a: the song + a sound effect mixed in)
  '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-movflags', '+faststart', out]);   // no -shortest: it cut the master's last 3 frames
console.log(`wrote ${out}  (${(fs.statSync(out).size / 1e6).toFixed(1)} MB, ${((Date.now() - t0) / 60000).toFixed(1)} min)`);
