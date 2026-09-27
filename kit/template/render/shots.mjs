// Print the resolved shot list (id, scene, start, end, duration, transition, lyric lines inside) without rendering.
//   node render/shots.mjs            (add --json for machine-readable)
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { ROOT } from './serve.mjs';
import { FILM, pageScripts } from './film.mjs';
const stubCtx = new Proxy({}, { get: () => () => ({}) });
const doc = { createElement: () => ({ getContext: () => stubCtx, width: 0, height: 0 }) };
const win = { DT: {} };
// browser classes a scene file may touch at LOAD time (a missing one once silently dropped a whole reel)
const noop = () => {};
class Path2D { constructor() { for (const k of ['moveTo', 'lineTo', 'rect', 'arc', 'arcTo', 'ellipse', 'closePath', 'quadraticCurveTo', 'bezierCurveTo', 'roundRect', 'addPath']) this[k] = noop; } }
class Image { constructor() { this.onload = null; this.onerror = null; } set src(v) { this._src = v; } get src() { return this._src; } decode() { return Promise.resolve(); } }
class OffscreenCanvas { constructor(w, h) { this.width = w; this.height = h; } getContext() { return stubCtx; } }
const ctx = vm.createContext({ window: win, document: doc, console, Math, DT: win.DT, Path2D, Image, OffscreenCanvas, performance: { now: () => 0 } });
// load exactly what web/index.html loads, in its order (render/film.mjs pageScripts); /film.js comes from film.json
for (const f of pageScripts()) {
  if (f === 'film.js') { win.DT_FILM = FILM; continue; }
  let src;
  try { src = fs.readFileSync(path.join(ROOT, f), 'utf8'); } catch (e) { if (e.code === 'ENOENT') continue; throw e; }   // no manifest/clips yet
  vm.runInContext(src, ctx, { filename: f });
}
const D = win.DT; D.timing = win.DT_TIMING;
// painters register their shots from their scene files (DT.reel), so load those too
for (const f of (win.DT_SCENE_FILES || [])) {
  try { vm.runInContext(fs.readFileSync(path.join(ROOT, 'web', 'scenes', f), 'utf8'), ctx, { filename: f }); }
  catch (e) { if (e.code !== 'ENOENT') console.error(`(scene file ${f} did not load in the stub: ${e.message})`); }
}
const shots = D.buildShots(D.assembleTimeline ? D.assembleTimeline() : D.TIMELINE);
if (process.argv.includes('--json')) { console.log(JSON.stringify(shots.map((s) => ({ id: s.id, scene: s.scene, start: s.start, end: s.end, trans: s.tr }))));
} else {
  for (const s of shots) {
    const lines = D.timing.lines.filter((l) => l.start < s.end && l.end > s.start).map((l) => 'L' + l.i);
    const tr = s.tr && s.tr.type !== 'cut' ? `${s.tr.type}(${s.tr.dur})` : '';
    console.log(`${s.id.padEnd(16)} ${s.scene.padEnd(12)} ${s.start.toFixed(2).padStart(7)} -> ${s.end.toFixed(2).padStart(7)}  (${(s.end - s.start).toFixed(2).padStart(5)}s) ${tr.padEnd(12)} ${lines.join(' ')}`);
  }
}
