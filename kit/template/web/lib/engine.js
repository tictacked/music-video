// =============================================================================
// engine.js -- the music-video engine: Canvas2D scenes + WebGL2 finishing. Every film keeps its own frozen copy (a new
// film gets this one from the kit); the kit's test/regress.mjs checks a film's copy against the kit's, frame by frame.
//
// Looks (every key and its default: LOOK0 below), among them:
//   keepRed      everything to two inks (keepInk + keepPaper, split at keepLevel +- keepSoft) EXCEPT true red,
//                which is kept and pushed to keepRedCol. 0..1.
//   gmap         a 4-stop gradient map on luminance (gmapStops at gmapPos): a reel's limited palette.
//                True red survives it by gmapKeepRed (default 1). DT.GRADES holds named palettes (a film's vocab adds them).
//   invertKeepRed the x-ray negative (invert) leaves true red alone. Default 0.
// Transitions (TR_TYPES below), among them: 'shatter' (A breaks into glass shards from tr.at; tr.cells, tr.color = the
//   crack glint); 'jigsaw' (B assembles over A as jigsaw pieces, each locking in with a white rim); 'negflash' keeps
//   true red unless tr.keepRed === 0; 'static' snow takes tr.color.
// CLIPS: image-to-video clips as upscaled JPG frames (assets/clips/<name>/00000.jpg, 'clip:<name>/<frame>'); KEYED clips
//   (figures on flat colour) as PNG frames with alpha (assets/clipa/<name>/00000.png, 'clipa:<name>/<f>').
//   DT_CLIPS (assets/clips/clips.js) has their frame counts. K.s.use() (web/lib/shaft.js) is the way scenes touch them.
//
// The machinery: a frame is a PURE FUNCTION of its index. Nothing carries between frames except
// deterministic caches (decoded images, pre-tinted sprites). That is what lets the renderer split the song into
// chunks, render them in any order, in parallel, and resume.
//
// Per shot, per frame:
//   1. BASE  canvas2D <- scene.draw(g, ctx)        pictures, clips, type, shapes (the painter's world)
//   2. OVER  canvas2D <- scene.over(g, ctx)        optional: things ABOVE the look (type, credits, the select menu)
//   3. LOOK  WebGL: base -> look(ctx) {impact, invert, mono, duotone, halftone, posterize, blur, grade, leak, ...}
//            -> + over -> shot texture
// then the shot textures are joined by a TRANSITION and a POST pass adds the finish (grain, flash, shake, zoom).
// =============================================================================
(function () {
  'use strict';
  const DT = (window.DT = window.DT || {});
  const W = (DT.W = 1920), H = (DT.H = 1080);
  DT.FPS = 24;
  DT.TWOS = 2;              // a new "drawing" every 2 frames (boil, jitter): animating on twos
  DT.scenes = DT.scenes || {};
  DT.scene = (id, def) => { DT.scenes[id] = def; def.id = id; };

  // ---------------------------------------------------------------- math
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const inv = (a, b, x) => clamp((x - a) / (b - a));
  const smooth = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
  const ease = {
    linear: (t) => clamp(t), smooth,
    in: (t) => clamp(t) ** 2, out: (t) => 1 - (1 - clamp(t)) ** 2,
    in3: (t) => clamp(t) ** 3, out3: (t) => 1 - (1 - clamp(t)) ** 3,
    inOut: (t) => { t = clamp(t); return t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2; },
    sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * clamp(t)),
    expoOut: (t) => (t >= 1 ? 1 : 1 - 2 ** (-10 * clamp(t))),
    expoIn: (t) => (t <= 0 ? 0 : 2 ** (10 * clamp(t) - 10)),
    back: (t) => { t = clamp(t); const c = 1.70158; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2; },
    backIn: (t) => { t = clamp(t); const c = 1.70158; return (c + 1) * t ** 3 - c * t ** 2; },
    elastic: (t) => { t = clamp(t); if (t === 0 || t === 1) return t; return 2 ** (-10 * t) * Math.sin((t * 10 - 0.75) * (2 * Math.PI / 3)) + 1; },
    bounce: (t) => { t = clamp(t); const n = 7.5625, d = 2.75;
      if (t < 1 / d) return n * t * t; if (t < 2 / d) return n * (t -= 1.5 / d) * t + 0.75;
      if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + 0.9375; return n * (t -= 2.625 / d) * t + 0.984375; },
  };
  function fnv(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function h01(...ks) {
    let h = 0x9e3779b9 | 0;
    for (const k of ks) { h = Math.imul(h ^ (k | 0), 0x85ebca6b); h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35); h ^= h >>> 16; }
    return (h >>> 0) / 4294967296;
  }
  function vnoise1(x, seed = 0) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(h01(seed, i), h01(seed, i + 1), u); }
  function hexToRgb(hex) { const h = hex.replace('#', ''); const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; }
  DT.util = { clamp, lerp, inv, smooth, ease, fnv, h01, vnoise1, hexToRgb };

  // ---------------------------------------------------------------- palette
  // Named colours for scenes (ctx.pal is DT.pal) and the kit's defaults: the ground (void), type and marker ink (ink,
  // red), paper, the pop accents, and `accent`, the default colour of the handwriting, magic circles and bolts in K.s.
  // A film adds its own names (and sets `accent` to its lead colour) with Object.assign(DT.pal, {...}) in its vocab,
  // not by editing this table.
  DT.pal = {
    // grounds, inks, papers
    void: '#040406', ink: '#1a1418', black: '#0b0a0d', night: '#0b1024', navy: '#1c2747', dusk: '#4b2f63',
    paper: '#fbf6ea', cream: '#f7ecd2', white: '#fffdf8', grey: '#8d97a3', stone: '#8e9296', stoneDk: '#3a3d40',
    // reds and pinks
    red: '#8f0f1e', redDk: '#3d0409', redHi: '#d11f35', blood: '#e8123c', hotpink: '#ff5d8f', pink: '#ff4f9a', blush: '#ff9fae',
    // warm
    fire: '#ff7a1f', orange: '#ff8c1a', amber: '#f2a23a', gold: '#f2c14e', lemon: '#fff27a', sand: '#f1d9a8',
    dawn: '#ffd9a0', sunset: '#ff8a3d', wood: '#7a4a2a',
    // cool
    sky: '#8ccbef', skyblue: '#86d8ff', sea: '#10a5c4', teal: '#19c3b1', mint: '#9ff0d0', lime: '#8cff1a',
    leaf: '#8fd14f', violet: '#6a2bff', lilac: '#c9a7ff',
    // the kit's default accent: K.s.thought, K.s.stack, K.s.circle, K.s.ripple and K.s.bolt's 'bolt' draw in it
    accent: '#1fc8b4',
  };
  // colour = who is speaking or acting: films fill it with speaker name -> colour (K.s.who, K.s.say's rule and name tag)
  DT.pal.who = {};

  // ---------------------------------------------------------------- timing (song/timing.json)
  DT.timing = null;
  function beatAt(t) { const T = DT.timing; return (t - T.beat0) / (60 / T.bpm); }
  function timeOfBeat(x) { const T = DT.timing; return T.beat0 + x * 60 / T.bpm; }
  function envAt(name, t) {
    const T = DT.timing; if (!T || !T.env || !T.env[name]) return 0;
    const a = T.env[name], x = t * T.env.fps, i = Math.floor(x);
    if (i < 0) return a[0]; if (i >= a.length - 1) return a[a.length - 1];
    return lerp(a[i], a[i + 1], x - i);
  }
  // most recent hit in a sorted list at or before t (binary search); returns time or -1e9
  function lastHit(list, t) {
    let lo = 0, hi = list.length - 1, best = -1e9;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (list[m] <= t + 1e-6) { best = list[m]; lo = m + 1; } else hi = m - 1; }
    return best;
  }
  DT.beatAt = beatAt; DT.timeOfBeat = timeOfBeat; DT.envAt = envAt; DT.lastHit = lastHit;
  DT.bar = (n) => timeOfBeat(4 * n + ((DT.timing && DT.timing.barOffset) || 0));      // the start of bar n (seconds)

  // ---------------------------------------------------------------- the story state (an RP's status box, as data)
  // Many RPs print a status box every turn (`Day: 3 / Location: the lake / Items: ...`). DT.STATE holds it as data:
  // [songTime (s), patch] pairs, applied in order, so ctx.state at t = every patch up to t, merged (Object.assign).
  // Use it for anything the story tracks that several reels must agree on (the day, the place, who is on screen, the
  // ground scheme for K.s.ground). K.s.status / K.s.hud draw the box from it; `hud: false` = no corner card.
  // The DIRECTOR owns this table; painters read ctx.state and never invent it. e.g.
  //   DT.STATE = [[0, { hud: true, day: 1, location: 'the station' }], [42.5, { location: 'the lake' }]];
  DT.STATE = [[0, { hud: false }]];
  // keys snap to frames like shot starts (an unsnapped key showed the PREVIOUS state on a reel's first frame)
  DT.stateKey = (k) => Math.round(k * DT.FPS) / DT.FPS;
  DT.stateAt = (t) => { const st = {}; for (const [k, p] of DT.STATE) { if (DT.stateKey(k) > t + 1e-6) break; Object.assign(st, p); } return st; };

  // Anchor grammar (timeline + scenes):  BASE [+/-N(s|b|B)]* [|b or |B or |h]
  //   BASE: number (seconds) | B<n> (bar n) | L<n> (line n start) | L<n>e (line n end) | W<n>.<k> (word k of line n start)
  //         | W<n>.<k>e (word end) | S<n> (section n start) | S<n>e | END
  //   offsets in seconds (default), beats (b) or bars (B); |b / |B snap to the nearest beat / bar line,
  //   |h snaps to the nearest half-beat (8th note).
  DT.anchor = function (a) {
    if (typeof a === 'number') return a;
    const T = DT.timing;
    const m = /^\s*([A-Za-z]+[\d.]*e?|-?[\d.]+)((?:\s*[+-]\s*[\d.]+[bBs]?)*)\s*(\|[bBh])?\s*$/.exec(a);
    if (!m) throw new Error('bad anchor ' + a);
    let base = m[1], t;
    if (/^-?[\d.]+$/.test(base)) t = +base;
    else if (base === 'END') t = T.duration;
    else if (base[0] === 'L') { const e = base.endsWith('e'); const n = parseInt(base.slice(1)); const L = T.lines[n]; if (!L) throw new Error('no line ' + n); t = e ? L.end : L.start; }
    else if (base[0] === 'W') { const e = base.endsWith('e'); const [n, k] = base.slice(1).replace(/e$/, '').split('.').map(Number); const L = T.lines[n]; const w = L && L.words && L.words[k]; if (!w) throw new Error('no word ' + base); t = e ? w.e : w.s; }
    else if (base[0] === 'S') { const e = base.endsWith('e'); const n = parseInt(base.slice(1)); const S = T.sections[n]; if (!S) throw new Error('no section ' + n); t = e ? S.end : S.start; }
    else if (base[0] === 'B') t = timeOfBeat(4 * parseFloat(base.slice(1)) + (T.barOffset || 0));   // B<n>: bar n (beat0 + (4n + barOffset) beats)
    else throw new Error('bad anchor base ' + base);
    for (const o of (m[2].match(/[+-]\s*[\d.]+[bBs]?/g) || [])) {
      const sign = o[0] === '-' ? -1 : 1, unit = /[bBs]$/.test(o) ? o.slice(-1) : 's', v = parseFloat(o.slice(1).replace(/[bBs]$/, ''));
      if (unit === 's') t += sign * v;
      else t = timeOfBeat(beatAt(t) + sign * v * (unit === 'B' ? 4 : 1));
    }
    if (m[3] === '|b') t = timeOfBeat(Math.round(beatAt(t)));
    if (m[3] === '|h') t = timeOfBeat(Math.round(beatAt(t) * 2) / 2);
    if (m[3] === '|B') { const bo = T.barOffset || 0; t = timeOfBeat(Math.round((beatAt(t) - bo) / 4) * 4 + bo); }
    return t;
  };

  // ---------------------------------------------------------------- shots + transitions
  // timeline entry: { id, scene, at, params?, trans?: {type, dur=0.5, align=0.5, ...params} }
  // A shot runs [start, next.start). Its `trans` joins it to the PREVIOUS shot: the window is
  // [start - dur*align, start + dur*(1-align)] (align 0.5 = centred on the cut, which is usually on a beat).
  DT.shots = [];
  DT.buildShots = function (timeline) {
    // starts snap to the NEAREST FRAME: beats can sit a few ms after a frame boundary (e.g. 0.253 + 0.5k vs k/24), so
    // an unsnapped cut first showed a whole frame (~40 ms) after the beat
    const shots = timeline.map((s, i) => ({ ...s, idx: i, start: Math.round(DT.anchor(s.at) * DT.FPS) / DT.FPS, seed: fnv(s.id || ('shot' + i)) }));
    for (let i = 0; i < shots.length; i++) shots[i].end = i + 1 < shots.length ? shots[i + 1].start : DT.timing.duration;
    DT.shots = shots.filter((s) => s.scene);
    for (const s of DT.shots) {
      if (s.end <= s.start) console.warn('shot has no length', s.id, s.start, s.end);
      const tr = s.trans || { type: 'cut' };
      const dur = tr.type === 'cut' ? 0 : (tr.dur != null ? tr.dur : 0.5), align = tr.align != null ? tr.align : 0.5;
      s.tr = { ...tr, dur, align, t0: s.start - dur * align, t1: s.start + dur * (1 - align) };
    }
    return DT.shots;
  };
  function shotIndexAt(t) { const S = DT.shots; let k = 0; for (let i = 0; i < S.length; i++) if (S[i].start <= t + 1e-6) k = i; return k; }
  DT.shotIndexAt = shotIndexAt;

  // ---------------------------------------------------------------- assets (images, clip frames)
  // keys: 'cut:hero_lean/12' (cut-out PNG, alpha)  'gen:env_shop/7' (whole picture)  'ref:cover'
  //       'song:cover'  'clip:<name>/<frame>' (video frames, jpg)  'file:<path from project root>'
  const imgs = new Map();      // key -> {img, promise, used}
  let useClock = 0;
  DT.assetURL = function (key) {
    const i = key.indexOf(':'); const kind = key.slice(0, i), k = key.slice(i + 1);
    if (kind === 'cut') return `/assets/cut/${k}.png`;
    if (kind === 'gen') return `/assets/gen/${k}.png`;
    if (kind === 'ref') return `/assets/ref/${k}.png`;
    if (kind === 'song') return `/song/${k}.png`;
    if (kind === 'art') return `/assets/art/${k}.png`;
    if (kind === 'clip') { const [name, f] = k.split('/'); return `/assets/clips/${name}/${String(+f).padStart(5, '0')}.jpg`; }
    if (kind === 'clipa') { const [name, f] = k.split('/'); return `/assets/clipa/${name}/${String(+f).padStart(5, '0')}.png`; }   // keyed (alpha)
    if (kind === 'file') return '/' + k;
    throw new Error('bad asset key ' + key);
  };
  DT.load = function (key) {
    let e = imgs.get(key);
    if (!e) {
      const img = new Image();
      img.decoding = 'async';
      const promise = new Promise((res, rej) => {
        img.onload = () => img.decode().then(() => res(img), () => res(img));
        img.onerror = () => rej(new Error('asset failed to load: ' + key + ' (' + DT.assetURL(key) + ')'));
      });
      img.src = DT.assetURL(key);
      e = { img, promise, ok: false, used: 0 };
      promise.then(() => { e.ok = true; }, () => {});
      imgs.set(key, e);
    }
    e.used = ++useClock;
    return e.promise;
  };
  DT.img = function (key) {    // synchronous: the engine guarantees scene.assets() were loaded first
    const e = imgs.get(key);
    if (!e || !e.ok) { DT.missing = (DT.missing || new Set()); DT.missing.add(key); DT.load(key).catch(() => {}); return null; }
    e.used = ++useClock;
    return e.img;
  };
  // clip frames are 1920x1108 JPGs (~8.5 MB decoded each): keep only the most recent `max` of them per browser, and
  // drop the pixels of evicted ones (a full render walks ~6800 of them; 500 cached = 4 GB of RAM per worker)
  function evict(max = 96) {
    // clip frames, keyed frames, and per-frame file: sequences (NNNNN.png, e.g. a scene's per-frame mattes)
    const arr = [...imgs.entries()].filter(([k]) => k.startsWith('clip:') || k.startsWith('clipa:') || /^file:.*[/][0-9]{5}[.]png$/.test(k));
    if (arr.length <= max) return;
    arr.sort((a, b) => a[1].used - b[1].used);
    for (const [k, e] of arr.slice(0, arr.length - max)) { try { e.img.removeAttribute('src'); } catch (err) {} imgs.delete(k); }
  }

  // ---------------------------------------------------------------- context for scenes
  function makeCtx(shot, t, tc) {
    const T = DT.timing;
    const drawing = Math.floor(Math.round(t * DT.FPS) / DT.TWOS);
    const tw = drawing * DT.TWOS / DT.FPS;
    const b = beatAt(t);
    const bo = T.barOffset || 0;
    const bar = (b - bo) / 4;
    const lt = t - shot.start, dur = shot.end - shot.start;
    const kickT = lastHit(T.kicks, t), snT = lastHit(T.snares, t);
    const at = (a) => Math.round(DT.anchor(a) * DT.FPS) / DT.FPS;     // frame-snapped, like shot starts
    const ctx = {
      t, tc, tw, lt, dur, u: clamp(lt / dur), shot, id: shot.id, params: shot.params || {}, seed: shot.seed,
      drawing, beat: b, beatPhase: b - Math.floor(b), bar, barPhase: bar - Math.floor(bar),
      beatIn: beatAt(t) - beatAt(shot.start),
      env: { rms: envAt('rms', t), low: envAt('low', t), mid: envAt('mid', t), high: envAt('high', t), onset: envAt('onset', t) },
      kick: Math.exp(-(t - kickT) / 0.12), snare: Math.exp(-(t - snT) / 0.12),
      beatPulse: Math.exp(-(b - Math.floor(b)) * 60 / T.bpm / 0.12),
      at, since: (a) => t - at(a),
      // 0 before `a`, eases to 1 over `d` seconds after it
      after: (a, d = 0.3, e = ease.out) => e(clamp((t - at(a)) / Math.max(1e-6, d))),
      // a hit: 1 at time a, decaying with half-life-ish `d`
      hit: (a, d = 0.18) => { const x = t - at(a); return x < 0 ? 0 : Math.exp(-x / d); },
      line: (n) => T.lines[n], word: (n, k) => T.lines[n].words[k],
      lineNow: () => T.lines.find((L) => t >= L.start - 0.05 && t <= L.end + 0.15) || null,
      rnd: (...ks) => h01(shot.seed, ...ks),
      jit: (...ks) => h01(shot.seed, drawing, ...ks),
      jitter: (amp, ...ks) => (h01(shot.seed, drawing, ...ks) - 0.5) * 2 * amp,
      W, H, pal: DT.pal, U: DT.util, ease,
      // registration defaults for DT.regVec when a look sets reg: null (see ctx.reg below): fully merged, no kick pulse
      merge: 1,
      // the story state at t (DT.STATE: an RP's status box, the day, the place...)
      state: DT.stateAt(t), stateAt: (a) => DT.stateAt(typeof a === 'number' ? a : at(a)),
      // the voice: the vocal stem's loudness (0..1) -- type can breathe with the singer
      voc: envAt('voc', t),
      // the words being sung now (sung, not unsung), and the most recent word to start
      wordsNow: (pre = 0.02) => { const out = []; for (const L of T.lines) { if (t < L.start - 1 || t > L.end + 1) continue; for (const w of L.words) if (!w.unsung && t >= w.s - pre && t < w.e) out.push({ ...w, line: L.i }); } return out; },
      lastWord: () => { let best = null; for (const L of T.lines) { if (L.start > t + 0.01) break; for (const w of L.words) if (!w.unsung && w.s <= t + 1e-6 && (!best || w.s >= best.s)) best = { ...w, line: L.i }; } return best; },
    };
    ctx.reg = 0;       // DT.regVec's base offset (px) when a look sets reg: null
    return ctx;
  }
  DT.makeCtx = makeCtx;

  // ---------------------------------------------------------------- WebGL
  let gl, glCanvas, quad, progFX, progTR, progPost, texBase, texOver, fbs = [], fbOut;
  const cvBase = document.createElement('canvas'), cvOver = document.createElement('canvas');
  cvBase.width = cvOver.width = W; cvBase.height = cvOver.height = H;
  const gBase = cvBase.getContext('2d'), gOver = cvOver.getContext('2d');
  DT.gBase = gBase; DT.gOver = gOver;

  const VS = `#version 300 es
in vec2 aPos; out vec2 vUv;
void main(){ vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }`;

  const NOISE = `
float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), u.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y); }
float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++){ s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s; }
float lum(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }
// the cold field: corners first (the points), then the edges, then everything
float coldField(vec2 uv, float seed){
  vec2 p = abs(uv - 0.5) * 2.0; p.x *= 1.0;               // 0 centre .. 1 edge
  float g = pow(pow(p.x, 4.0) + pow(p.y, 4.0), 0.25);        // 1 on edges, 1.19 in corners
  vec2 q = uv * vec2(1.7778, 1.0);
  float w = fbm(q * 3.0 + seed) * 0.55 + fbm(q * 11.0 - seed) * 0.18;   // organic, inky edge
  return g + w * 0.6;
}`;

  const FS_FX = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uBase, uOver;
uniform float uCold, uWarm, uHalf, uHalfSize, uHalfAng, uDuo, uInvert, uImpact, uImpactRed, uSeed, uVig, uPosterize, uSat, uBright;
uniform vec3 uColdCol, uWarmCol, uDuoDark, uDuoLight, uHalfInk;
uniform vec2 uWarmAt;
uniform float uTime, uGradeAmt, uHal, uLeak, uVhs, uVhsRoll, uRipple, uRippleF, uSwirl, uHue, uLinen, uPaper, uMBlur, uRBlur;
uniform vec2 uMDir, uRAt;
uniform vec3 uGrade, uLeakCol; uniform vec2 uLeakAt, uSwirlAt;
// the seam (the picture pushed apart from a line), glitch slices, CRT phosphor, 1-bit mono
uniform float uSeam, uSeamAng, uGlitch, uScan, uMono, uMonoLevel, uFrameN, uRegOver;
uniform vec2 uReg;   // registration, per shot: green at +uReg, red+blue at -uReg (px); the over layer gets uRegOver of it
uniform vec2 uSeamAt; uniform vec3 uSeamCol, uMonoDark, uMonoLight;
uniform float uKeepRed, uKeepLevel, uKeepSoft; uniform vec3 uKeepInk, uKeepPaper, uKeepRedCol;   // red ink (keepRed)
// the PALETTE GRADE (a 4-stop gradient map on luminance, keeping TRUE red) + the red-keeping invert
uniform float uGmap, uGmapKeepRed, uInvertKeepRed; uniform vec3 uG0, uG1, uG2, uG3; uniform vec4 uGpos;
${NOISE}
void main(){
  // distortions first (they move where the picture is sampled): 60s dream ripple, tie-dye swirl, VHS line jitter
  vec2 uv = vUv;
  float seamMask = 0.0;
  if (uSeam > 0.0) {          // the seam: the picture is pushed apart from a line through uSeamAt (angle 0 = vertical)
    vec2 n = vec2(cos(uSeamAng), sin(uSeamAng));
    vec2 px = (uv - uSeamAt) * vec2(1920.0, 1080.0);
    float d = dot(px, n);
    float hw = uSeam * 0.5;
    if (abs(d) < hw) seamMask = 1.0;
    else uv -= n * sign(d) * hw / vec2(1920.0, 1080.0);
  }
  if (uGlitch > 0.0) {        // datamosh-ish: bands of the picture slip sideways, a few blocks jump
    float fr = floor(uFrameN / 2.0);
    float band = floor(uv.y * mix(12.0, 48.0, hash(vec2(fr, 3.0))));
    float r = hash(vec2(band, fr));
    uv.x += step(1.0 - 0.35 * uGlitch, r) * (hash(vec2(band, fr + 7.0)) - 0.5) * 0.18 * uGlitch;
    vec2 blk = floor(uv * vec2(32.0, 18.0));
    if (hash(blk + fr) > 1.0 - 0.04 * uGlitch) uv += (vec2(hash(blk + 1.3), hash(blk + 2.1)) - 0.5) * 0.06;
  }
  if (uRipple > 0.0) uv.x += sin(uv.y * uRippleF + uTime * 7.0) * 0.02 * uRipple;
  if (uSwirl != 0.0) {
    vec2 q = (uv - uSwirlAt) * vec2(1.7778, 1.0);
    float r = length(q), a = uSwirl * exp(-r * r * 2.2);
    float cs = cos(a), sn = sin(a);
    q = mat2(cs, -sn, sn, cs) * q;
    uv = uSwirlAt + q / vec2(1.7778, 1.0);
  }
  if (uVhs > 0.0) {
    float line = floor(uv.y * 270.0), fr = floor(uTime * 24.0);
    float band = smoothstep(0.05, 0.0, abs(fract(uv.y * 0.5 + uTime * uVhsRoll * 0.4) - 0.5) - 0.42);   // a rolling tracking band
    uv.x += (hash(vec2(line, fr)) - 0.5) * 0.004 * uVhs + band * 0.035 * uVhs * (hash(vec2(line * 0.37, fr)) - 0.3);
  }
  // speed blur: directional (uMBlur px along uMDir: pans, rushes) and/or radial (uRBlur toward uRAt: a zoom burst)
  vec4 b;
  vec2 rg = uReg / vec2(1920.0, 1080.0);
  if (uMBlur > 0.0 || uRBlur > 0.0) {
    vec4 acc = vec4(0.0);
    for (int i = 0; i < 16; i++) {
      float f = float(i) / 15.0 - 0.5;
      vec2 o = uMDir * uMBlur * f / vec2(1920.0, 1080.0);
      vec2 r = (uv - uRAt) * (1.0 - uRBlur * 0.14 * (f + 0.5));
      vec2 P = uRAt + r + o;
      acc += vec4(texture(uBase, P - rg).r, texture(uBase, P + rg).g, texture(uBase, P - rg).b, 1.0);
    }
    b = acc / 16.0;
  } else b = vec4(texture(uBase, uv - rg).r, texture(uBase, uv + rg).g, texture(uBase, uv - rg).b, 1.0);
  vec3 c = b.rgb;
  if (uVhs > 0.0) {       // chroma bleed
    float o = 0.004 * uVhs;
    c.r = mix(c.r, texture(uBase, uv + vec2(o, 0.0)).r, 0.8);
    c.b = mix(c.b, texture(uBase, uv - vec2(o, 0.0)).b, 0.8);
  }
  // saturation / brightness trims
  float L = lum(c);
  c = mix(vec3(L), c, uSat); c *= uBright;
  // the palette grade (see the uniforms): luminance -> uG0..uG3 at uGpos; true red survives by uGmapKeepRed
  if (uGmap > 0.0) {
    vec3 src = c;
    float l = clamp(lum(c), 0.0, 1.0);
    vec3 gm;
    if (l < uGpos.y) gm = mix(uG0, uG1, clamp((l - uGpos.x) / max(1e-4, uGpos.y - uGpos.x), 0.0, 1.0));
    else if (l < uGpos.z) gm = mix(uG1, uG2, clamp((l - uGpos.y) / max(1e-4, uGpos.z - uGpos.y), 0.0, 1.0));
    else gm = mix(uG2, uG3, clamp((l - uGpos.z) / max(1e-4, uGpos.w - uGpos.z), 0.0, 1.0));
    float mx = max(src.r, max(src.g, src.b)), mn = min(src.r, min(src.g, src.b));
    float sat = (mx - mn) / (mx + 1e-4);
    float lean = (src.g - src.b) / max(mx - mn, 1e-4);          // orange leans green-over-blue; true red doesn't
    float red = step(max(src.g, src.b), src.r) * smoothstep(0.45, 0.6, sat) * smoothstep(0.28, 0.4, mx) * (1.0 - smoothstep(0.12, 0.3, lean));
    c = mix(c, gm, uGmap);
    c = mix(c, src, red * uGmapKeepRed * uGmap);
  }
  // duotone: luminance -> [dark, light]
  if (uDuo > 0.0) { float l = lum(c); c = mix(c, mix(uDuoDark, uDuoLight, smoothstep(0.02, 0.98, l)), uDuo); }
  // posterize (pop flat)
  if (uPosterize > 0.0) { float n = uPosterize; c = floor(c * n + 0.5) / n; }
  // halftone dot screen (pop-art Ben-Day), darkens where the picture is dark
  if (uHalf > 0.0) {
    float s = sin(uHalfAng), co = cos(uHalfAng);
    vec2 px = vUv * vec2(1920.0, 1080.0);
    vec2 r = mat2(co, -s, s, co) * px / uHalfSize;
    vec2 cell = fract(r) - 0.5;
    float l = lum(c);
    float rad = sqrt(clamp(1.0 - l, 0.0, 1.0)) * 0.62;
    float dotm = 1.0 - smoothstep(rad - 0.06, rad + 0.06, length(cell));
    vec3 ht = mix(vec3(1.0), uHalfInk, dotm);
    c = mix(c, c * ht + (1.0 - ht) * 0.0, uHalf);
  }
  // x-ray: the negative (white <-> black)
  if (uInvert > 0.0) {    // with invertKeepRed, true red survives the x-ray negative
    float mx0 = max(c.r, max(c.g, c.b)), mn0 = min(c.r, min(c.g, c.b));
    float red0 = uInvertKeepRed * step(max(c.g, c.b), c.r) * smoothstep(0.45, 0.6, (mx0 - mn0) / (mx0 + 1e-4)) * smoothstep(0.28, 0.4, mx0);
    vec3 n = vec3(1.0) - c; n = mix(vec3(lum(n)), n, 0.4) * vec3(0.85, 0.95, 1.08); n = mix(n, c, red0); c = mix(c, n, uInvert);
  }
  // impact frame: reduce to white / black / red
  if (uImpact > 0.0) {
    float l = lum(c);
    // true red has green ~ blue; orange (fur, hair, rust) has green >> blue and must NOT read as blood
    float redness = clamp((c.r - max(c.g, c.b)) * 3.0 - 0.4, 0.0, 1.0) * clamp(1.0 - (c.g - c.b) * 4.0, 0.0, 1.0);
    vec3 bw = l > 0.5 ? vec3(0.985, 0.965, 0.93) : vec3(0.086, 0.07, 0.10);
    vec3 imp = mix(bw, vec3(1.0, 0.165, 0.24), redness * uImpactRed);   // impact frames are black/white unless a shot asks for red (impactRed): with red always on, pink pastels went red
    c = mix(c, imp, uImpact);
  }
  // warm: a white-hot pink bloom from uWarmAt (a gaze, a blush)
  if (uWarm > 0.0) {
    float d = length((vUv - uWarmAt) * vec2(1.7778, 1.0));
    float r = exp(-d * d * 2.2) * uWarm;
    c = 1.0 - (1.0 - c) * (1.0 - uWarmCol * r * 0.9);          // screen
    c = mix(c, vec3(1.0, 0.97, 0.95), clamp(uWarm - 0.6, 0.0, 1.0) * 1.2 * exp(-d * d * 1.2));
  }
  // cold: ink from the points -- swallows the picture, but NOT the over layer (glowing eyes, type)
  if (uCold > 0.0) {
    float f = coldField(vUv, uSeed);
    float th = 1.62 - uCold * 1.6;       // 0.1 = a touch in the corners, 0.3 = the edges, 0.6 = most, 1 = all
    float m = smoothstep(th - 0.006, th + 0.006, f);
    // spatter: a few droplets just inside the front
    float sp = step(0.985, hash(floor(vUv * vec2(160.0, 90.0)) + uSeed)) * smoothstep(th - 0.18, th - 0.02, f);
    m = max(m, sp);
    c = mix(c, uColdCol, m);
  }
  // hue rotation about the grey axis (the whole rainbow turns)
  if (uHue != 0.0) { vec3 k = vec3(0.57735); float ca = cos(uHue); c = c * ca + cross(k, c) * sin(uHue) + k * dot(k, c) * (1.0 - ca); }
  // grade: light of a colour (dawn pink, noon white, golden hour amber, blue hour, cyanotype night)
  if (uGradeAmt > 0.0) { vec3 gc = uGrade / max(0.05, lum(uGrade)); c = mix(c, c * gc, uGradeAmt); }
  // halation: film highlights bloom with a warm red fringe
  if (uHal > 0.0) {
    vec3 acc = vec3(0.0);
    for (int i = 0; i < 12; i++) { float a = float(i) * 0.5236; vec2 o = vec2(cos(a) / 1920.0, sin(a) / 1080.0) * 14.0 * (1.0 + float(i % 3)); acc += texture(uBase, uv + o).rgb; }
    acc /= 12.0;
    vec3 ex = max(acc - 0.62, 0.0);
    c += ex * vec3(1.0, 0.42, 0.22) * uHal * 1.6;
  }
  // light leak: a warm organic burn from uLeakAt (the end of a roll)
  if (uLeak > 0.0) {
    vec2 q = (vUv - uLeakAt) * vec2(1.7778, 1.0);
    float d = length(q) + (fbm(vUv * 2.5 + uSeed + uTime * 0.15) - 0.5) * 0.45;
    float lg = clamp(exp(-d * d * 3.0) * uLeak, 0.0, 1.0);
    vec3 lc = mix(uLeakCol, vec3(1.0, 0.93, 0.78), smoothstep(0.55, 1.0, lg));
    c = 1.0 - (1.0 - c) * (1.0 - lc * lg);
  }
  // linen postcard: embossed weave + saturated inks (the old linen-finish "Greetings from" postcards)
  if (uLinen > 0.0) {
    vec2 px = vUv * vec2(1920.0, 1080.0);
    float wv = 0.5 + 0.25 * sin(px.x * 1.9) + 0.25 * sin(px.y * 1.9 + sin(px.x * 0.05) * 2.0);
    float fib = vnoise(px * vec2(0.9, 0.08)) * 0.5 + vnoise(px * vec2(0.08, 0.9)) * 0.5;
    float tx = mix(1.0, 0.86 + 0.14 * (wv * 0.6 + fib * 0.4), uLinen);
    c = mix(vec3(lum(c)), c, 1.0 + 0.35 * uLinen) * tx;
  }
  // paper tooth (postcards, prints, anything printed)
  if (uPaper > 0.0) { vec2 px = vUv * vec2(1920.0, 1080.0); float f = fbm(px * 0.02) * 0.6 + vnoise(px * 0.35) * 0.4; c *= 1.0 - uPaper * (f - 0.3) * 0.25; }
  // VHS finish: scanlines, snow, washed chroma
  if (uVhs > 0.0) {
    c *= mix(1.0, 0.92 + 0.08 * sin(vUv.y * 1080.0 * 1.5708), uVhs);
    float sn = step(0.997, hash(vUv * vec2(640.0, 360.0) + fract(uTime * 13.0)));
    c = mix(c, vec3(1.0), sn * uVhs * 0.6);
    c = mix(c, vec3(lum(c)) * vec3(0.95, 1.0, 1.08), 0.25 * uVhs);
  }
  if (uVig > 0.0) { float d = length((vUv - 0.5) * vec2(1.3, 1.0)); c *= 1.0 - uVig * smoothstep(0.35, 0.95, d); }
  // RED INK (keepRed). Everything becomes two inks (ink + paper, soft edge) EXCEPT red, which is kept and pushed to
  // keepRedCol: a red / black / white poster look out of any picture or clip. Pale skin and rosy cheeks stay paper.
  if (uKeepRed > 0.0) {
    float mx = max(c.r, max(c.g, c.b)), mn = min(c.r, min(c.g, c.b)), sat = (mx - mn) / max(mx, 1e-4);
    // red = far above green AND blue, with green ~ blue (brown hair, skin, amber, orange all have g > b: never red)
    float red = smoothstep(0.35, 0.55, sat) * smoothstep(0.18, 0.32, c.r - max(c.g, c.b)) * (1.0 - smoothstep(0.02, 0.10, c.g - c.b));
    float l = lum(c);
    vec3 bw = mix(uKeepInk, uKeepPaper, smoothstep(uKeepLevel - uKeepSoft, uKeepLevel + uKeepSoft, l));
    vec3 rd = mix(uKeepRedCol * 0.5, uKeepRedCol, smoothstep(0.15, 0.55, l));
    c = mix(c, mix(bw, rd, red), uKeepRed);
  }
  // 1-bit: the picture as two inks (vocaloid stark), threshold uMonoLevel
  if (uMono > 0.0) { float l = lum(c); c = mix(c, mix(uMonoDark, uMonoLight, step(uMonoLevel, l)), uMono); }
  // CRT phosphor: scanlines + an RGB triad mask + a little bloom of the brights (a terminal, an old monitor)
  if (uScan > 0.0) {
    float sl = 0.62 + 0.38 * pow(abs(sin(vUv.y * 1080.0 * 1.5708 * 0.6667)), 1.5);
    float tri = mod(floor(vUv.x * 1920.0), 3.0);
    vec3 mask = vec3(tri == 0.0 ? 1.0 : 0.78, tri == 1.0 ? 1.0 : 0.78, tri == 2.0 ? 1.0 : 0.78);
    c = mix(c, c * sl * mask * 1.25, uScan);
  }
  if (seamMask > 0.0) c = uSeamCol;
  // over layer (premultiplied) sits above the whole look
  vec2 ro = rg * uRegOver;
  vec4 ovR = texture(uOver, vUv - ro), ovG = texture(uOver, vUv + ro);
  c = vec3(ovR.r + c.r * (1.0 - ovR.a), ovG.g + c.g * (1.0 - ovG.a), ovR.b + c.b * (1.0 - ovR.a));
  o = vec4(c, 1.0);
}`;

  // transition masks: 0 at A, 1 at B. uP = progress 0..1 through the window.
  const FS_TR = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uA, uB;
uniform int uType; uniform float uP, uSeed; uniform vec4 uPar; uniform vec3 uCol; uniform vec2 uAt;
${NOISE}
float dot2(vec2 v){ return dot(v, v); }
vec2 mirror2(vec2 q){ return 1.0 - abs(1.0 - mod(q, 2.0)); }   // mirror-repeat (the zoom's incoming shot: mirrored past its edges, not smeared)
float heartSD(vec2 p){   // iq's exact heart SDF, recentred: tip at y=-0.5, lobes up to ~+0.55 (GL y is up)
  p.y += 0.5; p.x = abs(p.x);
  if (p.y + p.x > 1.0) return sqrt(dot2(p - vec2(0.25, 0.75))) - sqrt(2.0) / 4.0;
  return sqrt(min(dot2(p - vec2(0.0, 1.0)), dot2(p - 0.5 * max(p.x + p.y, 0.0)))) * sign(p.x - p.y);
}
// glass shards = a jittered-grid Voronoi. shSeed(cell) = the cell's seed point; shNear(q) = (nearest cell, d2 - d1)
vec2 shSeed(vec2 cell){ return cell + 0.15 + 0.7 * vec2(hash(cell + 11.3), hash(cell + 27.9)); }
vec3 shNear(vec2 q){
  vec2 b = floor(q), best = b; float d1 = 1e9, d2 = 1e9;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 cell = b + vec2(float(i), float(j)); float d = length(q - shSeed(cell));
    if (d < d1) { d2 = d1; d1 = d; best = cell; } else if (d < d2) { d2 = d; }
  }
  return vec3(best, d2 - d1);
}
// the jigsaw piece that owns a point in piece space (y down). Knob signs per edge: vertical +1 bulges
// toward +x, horizontal +1 bulges up (-y). A knob = a circle r 0.21 centred 0.17 inside the receiving cell.
vec2 jigOwner(vec2 P, vec2 nc, float seed){
  vec2 cell = floor(P), f = P - cell, own = cell;
  float r = 0.21, off = 0.17;
  float sR = hash(vec2(cell.x + 1.0, cell.y) + seed * 1.7) > 0.5 ? 1.0 : -1.0;
  float sL = hash(vec2(cell.x, cell.y) + seed * 1.7) > 0.5 ? 1.0 : -1.0;
  float sB = hash(vec2(cell.x, cell.y + 1.0) + seed * 3.1) > 0.5 ? 1.0 : -1.0;
  float sT = hash(vec2(cell.x, cell.y) + seed * 3.1) > 0.5 ? 1.0 : -1.0;
  if (cell.x < nc.x - 1.0 && sR < 0.0 && length(f - vec2(1.0 - off, 0.5)) < r) own = cell + vec2(1.0, 0.0);
  if (cell.x > 0.0 && sL > 0.0 && length(f - vec2(off, 0.5)) < r) own = cell - vec2(1.0, 0.0);
  if (cell.y < nc.y - 1.0 && sB > 0.0 && length(f - vec2(0.5, 1.0 - off)) < r) own = cell + vec2(0.0, 1.0);
  if (cell.y > 0.0 && sT < 0.0 && length(f - vec2(0.5, off)) < r) own = cell - vec2(0.0, 1.0);
  return own;
}
void main(){
  vec4 A = texture(uA, vUv), B = texture(uB, vUv);
  float p = uP; vec3 c; vec2 asp = vec2(1.7778, 1.0);
  if (uType == 1) {            // dissolve
    c = mix(A.rgb, B.rgb, smoothstep(0.0, 1.0, p));
  } else if (uType == 2) {     // dip through uCol
    c = p < 0.5 ? mix(A.rgb, uCol, smoothstep(0.0, 0.5, p)) : mix(uCol, B.rgb, smoothstep(0.5, 1.0, p));
  } else if (uType == 3) {     // flash: hard cut at 0.5 under a white-hot flash
    float f = 1.0 - abs(p - 0.5) * 2.0; c = mix(p < 0.5 ? A.rgb : B.rgb, uCol, pow(f, 1.5));
  } else if (uType == 4) {     // ink: cold floods in from the points, then drains away revealing B
    float f = coldField(vUv, uSeed);
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0;
    float th = 1.75 - k * 1.8;
    float m = smoothstep(th - 0.006, th + 0.006, f);
    c = mix(p < 0.5 ? A.rgb : B.rgb, uCol, m);
  } else if (uType == 5) {     // blush: a pink-white bloom from uAt covers A, then clears onto B
    float d = length((vUv - uAt) * asp);
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0;
    float r = k * 2.4;
    float m = smoothstep(r, r - 0.35, d + fbm(vUv * 6.0 + uSeed) * 0.15);
    // peaks PINK with a soft light core (a blush, not a white-out)
    vec3 bl = mix(uCol, vec3(1.0, 0.97, 0.96), 0.55 * smoothstep(r - 0.1, r - 0.9, d));
    c = mix(p < 0.5 ? A.rgb : B.rgb, bl, m * smoothstep(0.0, 0.2, k));
  } else if (uType == 6) {     // heart iris: B grows inside a heart centred at uAt
    vec2 q = (vUv - uAt) * asp;
    float s = mix(0.001, 3.6, p * p);   // 3.6: the heart covers the bottom corners at p=1
    float d = heartSD(q / s) * s;
    float edge = smoothstep(0.0, -0.02, d) ;
    float rim = smoothstep(0.014, 0.0, abs(d)) * step(0.01, p) * step(p, 0.99);
    c = mix(A.rgb, B.rgb, edge);
    c = mix(c, uCol, rim);
  } else if (uType == 7) {     // slash: a diagonal cut sweeps across (uPar.x = angle rad), white hot edge
    float ang = uPar.x; vec2 n = vec2(cos(ang), sin(ang));
    float d = dot((vUv - 0.5) * asp, n);
    float front = mix(-1.3, 1.3, p);
    float m = smoothstep(front + 0.003, front - 0.003, d);
    float rim = smoothstep(0.02, 0.0, abs(d - front));
    c = mix(A.rgb, B.rgb, m); c = mix(c, uCol, rim);
  } else if (uType == 8) {     // wipe: uPar.xy = direction
    vec2 n = normalize(uPar.xy); float d = dot(vUv - 0.5, n) + 0.5 * (abs(n.x) + abs(n.y));
    float m = smoothstep(p * 1.2 - 0.1, p * 1.2 - 0.1 - 0.02, d / (abs(n.x) + abs(n.y)));
    c = mix(A.rgb, B.rgb, m);
  } else if (uType == 9) {     // tear: a torn paper edge sweeps left->right, with a white fibrous margin
    float y = vUv.y;
    float jag = (fbm(vec2(y * 18.0, uSeed)) - 0.5) * 0.12 + (hash(vec2(floor(y * 140.0), uSeed)) - 0.5) * 0.02;
    float front = mix(-0.15, 1.15, p) + jag;
    float m = step(vUv.x, front);
    float rim = smoothstep(0.025, 0.0, abs(vUv.x - front - 0.012)) * (0.7 + 0.3 * hash(vUv * 400.0));
    c = mix(A.rgb, B.rgb, m); c = mix(c, uCol, rim);
  } else if (uType == 10) {    // blink: eyelids close on A (p<.5) and open on B
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0;           // 0 open .. 1 shut
    float x = (vUv.x - 0.5) * 1.7778;
    float lid = mix(0.62, -0.02, pow(k, 0.8));                // half-height of the opening
    float curve = lid * (1.0 - x * x * 0.35);
    float m = smoothstep(curve, curve + 0.01, abs(vUv.y - 0.5));
    c = mix(p < 0.5 ? A.rgb : B.rgb, uCol, m);
  } else if (uType == 11) {    // zoom through: A rushes in toward uAt, B arrives from small
    float k = smoothstep(0.0, 1.0, p);
    vec2 za = uAt + (vUv - uAt) / (1.0 + k * 6.0);
    vec2 zb = uAt + (vUv - uAt) * (1.0 + (1.0 - k) * 2.5);
    vec3 a = vec3(0.0), bb = vec3(0.0);
    for (int i = 0; i < 8; i++) { float f = float(i) / 8.0;
      a += texture(uA, uAt + (za - uAt) * (1.0 - f * 0.12 * k)).rgb; bb += texture(uB, mirror2(uAt + (zb - uAt) * (1.0 - f * 0.12 * (1.0 - k)))).rgb; }
    c = mix(a / 8.0, bb / 8.0, smoothstep(0.35, 0.65, p));
  } else if (uType == 12) {    // glitch: blocks of B punch through A, then take over
    vec2 blk = floor(vUv * vec2(24.0, 14.0));
    float r = hash(blk + floor(p * 9.0) + uSeed);
    float m = step(r, p * 1.15 - 0.05);
    vec2 off = vec2((hash(blk.yy + floor(p * 17.0)) - 0.5) * 0.08 * (1.0 - abs(p - 0.5) * 2.0), 0.0);
    vec3 a = vec3(texture(uA, vUv + off).r, texture(uA, vUv).g, texture(uA, vUv - off).b);
    vec3 bb = vec3(texture(uB, vUv - off).r, texture(uB, vUv).g, texture(uB, vUv + off).b);
    c = mix(a, bb, m);
  } else if (uType == 13) {    // circle iris at uAt
    float d = length((vUv - uAt) * asp); float r = p * 2.2;
    c = mix(A.rgb, B.rgb, smoothstep(r + 0.004, r - 0.004, d));
    c = mix(c, uCol, smoothstep(0.012, 0.0, abs(d - r)) * step(0.005, p) * step(p, 0.995));
  } else if (uType == 14) {    // blinds: horizontal slats
    float s = fract(vUv.y * uPar.x); c = mix(A.rgb, B.rgb, step(s, p));
  } else if (uType == 15) {    // mosaic: A pixelates up, B pixelates down
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0; float n = mix(1080.0, 12.0, pow(k, 0.5));
    vec2 g = (floor(vUv * vec2(n * 1.7778, n)) + 0.5) / vec2(n * 1.7778, n);
    c = p < 0.5 ? texture(uA, g).rgb : texture(uB, g).rgb;
  } else if (uType == 16) {    // split: A slides apart (two halves) revealing B
    float k = smoothstep(0.0, 1.0, p);
    float off = k * 0.55;
    if (vUv.x < 0.5 - off || vUv.x > 0.5 + off) {
      vec2 s = vUv.x < 0.5 ? vUv + vec2(off, 0.0) : vUv - vec2(off, 0.0);
      c = texture(uA, s).rgb;
    } else c = B.rgb;
  } else if (uType == 17) {    // checker: cells flip in a diagonal wave
    vec2 cell = floor(vUv * vec2(16.0, 9.0));
    float d = (cell.x + cell.y) / 24.0;
    c = mix(A.rgb, B.rgb, step(d, p * 1.1));
  } else if (uType == 18) {    // wave: a breaking wave sweeps across (uPar.x +1 = left->right), B behind the water
    float x = uPar.x >= 0.0 ? vUv.x : 1.0 - vUv.x, y = vUv.y;
    float fr = mix(-0.3, 1.35, p) + (y - 0.5) * 0.18 + sin(y * 9.0 + p * 7.0) * 0.025 + (fbm(vec2(y * 5.0, p * 2.0 + uSeed)) - 0.5) * 0.09;
    float d = x - fr, band = 0.26;
    if (d > 0.0) c = A.rgb;
    else {
      float k = clamp(-d / band, 0.0, 1.0);
      vec2 ref = vec2((fbm(vUv * 7.0 + p * 3.0) - 0.5) * 0.03, 0.0);
      vec3 wc = mix(uCol * 1.2, mix(texture(uB, vUv + ref).rgb, uCol, 0.35), k);
      c = mix(wc, B.rgb, smoothstep(0.55, 1.0, k));
      float foam = smoothstep(-0.11, -0.03, d) * (0.55 + 0.45 * step(0.45, hash(floor(vUv * vec2(260.0, 150.0)) + floor(p * 24.0))));
      foam = max(foam, smoothstep(0.012, 0.0, abs(d)));
      c = mix(c, vec3(0.97, 0.99, 1.0), clamp(foam, 0.0, 1.0));
    }
  } else if (uType == 19) {    // tide: the waterline rises over A, then drains away off B (the backwash)
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0;
    float lvl = mix(-0.12, 1.12, smoothstep(0.0, 1.0, k)) + sin(vUv.x * 14.0 + p * 20.0) * 0.012 + (fbm(vec2(vUv.x * 5.0, p * 4.0 + uSeed)) - 0.5) * 0.04;
    vec2 wob = vec2(sin(vUv.y * 40.0 + p * 30.0) * 0.004, 0.0);
    vec3 dry = p < 0.5 ? A.rgb : B.rgb;
    vec3 src = p < 0.5 ? texture(uA, vUv + wob).rgb : texture(uB, vUv + wob).rgb;
    vec3 wet = mix(src, uCol, 0.45 + 0.3 * smoothstep(0.0, 0.35, lvl - vUv.y));
    float under = smoothstep(lvl + 0.002, lvl - 0.002, vUv.y);
    float lace = smoothstep(0.012, 0.0, abs(vUv.y - lvl)) * (0.5 + 0.5 * hash(floor(vUv * vec2(400.0, 60.0)) + floor(p * 30.0)));
    c = mix(dry, wet, under); c = mix(c, vec3(0.97, 0.99, 1.0), lace);
  } else if (uType == 20) {    // ripple: the 60s TV dream dissolve (the picture wobbles as it melts into B)
    float k = sin(p * 3.14159);
    vec2 off = vec2(sin(vUv.y * 42.0 + p * 26.0) * 0.03 * k, 0.0);
    c = mix(texture(uA, vUv + off).rgb, texture(uB, vUv + off).rgb, smoothstep(0.25, 0.75, p));
    c = mix(c, vec3(1.0, 0.97, 0.92), 0.18 * k);
  } else if (uType == 21) {    // spin: A turns edge-on about the vertical axis (postcard / spinner rack), B turns in
    float th = (p < 0.5 ? p : 1.0 - p) * 3.14159;
    float w = max(cos(th), 0.0005), sd = uPar.x >= 0.0 ? 1.0 : -1.0;
    float xs = (vUv.x - 0.5) / w;
    float persp = 1.0 + xs * sin(th) * 0.5 * sd * (p < 0.5 ? 1.0 : -1.0);
    vec2 cu = vec2(xs + 0.5, (vUv.y - 0.5) / max(persp, 0.05) + 0.5);
    vec3 face = (p < 0.5 ? texture(uA, cu).rgb : texture(uB, cu).rgb) * (1.0 - sin(th) * 0.45);
    float inside = step(0.0, cu.x) * step(cu.x, 1.0) * step(0.0, cu.y) * step(cu.y, 1.0);
    c = mix(uCol, face, inside);
  } else if (uType == 22) {    // leak: a light-leak burn blooms from uAt, burns out amber-white, clears onto B
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0;
    vec2 q = (vUv - uAt) * asp;
    float d = length(q) + (fbm(vUv * 3.0 + uSeed + p * 0.8) - 0.5) * 0.5;
    float lg = exp(-d * d / max(0.001, k * k * 1.8));
    vec3 base = p < 0.5 ? A.rgb : B.rgb;
    vec3 lc = mix(uCol, vec3(1.0, 0.95, 0.8), smoothstep(0.5, 1.0, lg * k));
    c = 1.0 - (1.0 - base) * (1.0 - lc * clamp(lg * 1.2, 0.0, 1.0));
    c = mix(c, vec3(1.0, 0.97, 0.9), smoothstep(0.85, 1.0, k) * 0.9);
  } else if (uType == 23) {    // film: A rolls away up (uPar.x +1) or down (-1 = rewind), a frame line, B rolls in; streaked
    float dir = uPar.x >= 0.0 ? 1.0 : -1.0, k = smoothstep(0.0, 1.0, p), gap = 0.07, blur = sin(p * 3.14159) * 0.05;
    vec3 acc = vec3(0.0);
    for (int i = 0; i < 7; i++) {
      float y = vUv.y - dir * k * (1.0 + gap) + (float(i) / 6.0 - 0.5) * blur;
      float yb = y + dir * (1.0 + gap);
      if (y >= 0.0 && y <= 1.0) acc += texture(uA, vec2(vUv.x, y)).rgb;
      else if (yb >= 0.0 && yb <= 1.0) acc += texture(uB, vec2(vUv.x, yb)).rgb;
      else {
        float gy = y > 1.0 ? (y - 1.0) / gap : (-y) / gap;           // 0..1 across the frame line
        float hole = step(abs(fract(vUv.x * 22.0) - 0.5), 0.18) * step(abs(gy - 0.5), 0.22);
        acc += mix(uCol, vec3(0.93, 0.9, 0.82), hole * 0.8);
      }
    }
    c = acc / 7.0;
  } else if (uType == 24) {    // page: A peels from the bottom-right corner toward the top-left, B beneath
    vec2 P = vUv * asp;
    vec2 n = normalize(vec2(1.0, -0.3));
    float c0 = dot(vec2(0.0), n), c1 = dot(vec2(asp.x, 0.0), n), c2 = dot(vec2(0.0, 1.0), n), c3 = dot(asp, n);
    float fmax = max(max(c0, c1), max(c2, c3)) + 0.04, fmin = min(min(c0, c1), min(c2, c3)) - 0.04;
    float f = mix(fmax, fmin, p);
    float sP = dot(P, n) - f;
    if (sP > 0.0) c = B.rgb * (1.0 - 0.45 * exp(-sP * 22.0));
    else {
      vec2 qu = (P - 2.0 * sP * n) / asp;
      if (qu.x >= 0.0 && qu.x <= 1.0 && qu.y >= 0.0 && qu.y <= 1.0) c = mix(uCol, texture(uA, qu).rgb, 0.12) * (0.72 + 0.28 * smoothstep(0.0, 0.25, -sP));
      else c = A.rgb;
    }
  } else if (uType == 25) {    // star: B blooms inside a four-point Googie sparkle at uAt, turning
    vec2 q = (vUv - uAt) * asp;
    float ang = p * 1.2, cs = cos(ang), sn = sin(ang); q = mat2(cs, -sn, sn, cs) * q;
    vec2 a = abs(q) / mix(0.0005, 3.2, p * p);
    float f = sqrt(a.x) + sqrt(a.y);
    c = mix(A.rgb, B.rgb, smoothstep(1.03, 0.97, f));
    c = mix(c, uCol, smoothstep(0.08, 0.0, abs(f - 1.0)) * step(0.01, p) * step(p, 0.985));
  } else if (uType == 26) {    // whip: a whip pan -- A flies out sideways, B flies in, smeared (uPar.x +1 = content moves left)
    float dir = uPar.x >= 0.0 ? 1.0 : -1.0, k = smoothstep(0.0, 1.0, p), blur = sin(p * 3.14159) * 0.22;
    vec3 acc = vec3(0.0);
    for (int i = 0; i < 12; i++) {
      float xa = vUv.x + dir * k + (float(i) / 11.0 - 0.5) * blur, xb = xa - dir;
      acc += (xa >= 0.0 && xa <= 1.0) ? texture(uA, vec2(xa, vUv.y)).rgb : texture(uB, vec2(clamp(xb, 0.0, 1.0), vUv.y)).rgb;
    }
    c = acc / 12.0;
  } else if (uType == 27) {    // irisdip: the cartoon iris closes on A to uCol, then opens on B
    float k = p < 0.5 ? 1.0 - p * 2.0 : (p - 0.5) * 2.0;
    float d = length((vUv - uAt) * asp), r = pow(k, 1.3) * 2.1;
    c = mix(uCol, p < 0.5 ? A.rgb : B.rgb, smoothstep(r + 0.004, r - 0.004, d));
  } else if (uType == 28) {    // MERGE: B arrives as two halves from both edges and they meet on the seam (uPar.x 1 = top/bottom)
    float k = smoothstep(0.0, 1.0, p), off = (1.0 - k) * 0.5;
    bool hz = uPar.x > 0.5;
    float x = hz ? vUv.y : vUv.x;
    float bx = x < 0.5 ? x + off : x - off;
    bool inB = x < 0.5 ? bx < 0.5 : bx >= 0.5;
    vec2 buv = hz ? vec2(vUv.x, bx) : vec2(bx, vUv.y);
    c = inB ? texture(uB, buv).rgb : A.rgb;
    float edge = x < 0.5 ? 0.5 - off : 0.5 + off;
    c = mix(c, uCol, smoothstep(0.012, 0.0, abs(x - edge)) * step(0.02, off));
    c = mix(c, vec3(1.0), exp(-(1.0 - k) * 16.0) * exp(-abs(x - 0.5) * 60.0));   // the join flashes white
  } else if (uType == 29) {    // REG: A's plates fly out of register, B's plates fly into it
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0;
    vec2 d = vec2(cos(uPar.x), sin(uPar.x)) * pow(k, 1.6) * 0.07;
    if (p < 0.5) c = vec3(texture(uA, vUv - d).r, texture(uA, vUv + d).g, texture(uA, vUv - d).b);
    else c = vec3(texture(uB, vUv - d).r, texture(uB, vUv + d).g, texture(uB, vUv - d).b);
    c *= 1.0 + k * 0.35;
  } else if (uType == 30) {    // STATIC: a TV-static burst peaking at the cut (rolling bars, a flicker)
    float k = 1.0 - abs(p - 0.5) * 2.0;
    float fr = floor(p * 40.0);
    float n = hash(floor(vUv * vec2(480.0, 270.0)) + fr * 1.37);
    float bar = 0.75 + 0.25 * sin(vUv.y * 30.0 + p * 60.0);
    vec3 st = vec3(n * bar) * uCol;   // the snow takes tr.color (white by default)
    c = mix(p < 0.5 ? A.rgb : B.rgb, st, smoothstep(0.0, 0.35, k));
  } else if (uType == 31) {    // SLICES: horizontal bands switch A -> B one by one, slipping sideways as they go
    float nb = uPar.x > 0.0 ? uPar.x : 18.0;
    float band = floor(vUv.y * nb);
    float th = hash(vec2(band, uSeed));
    float m = step(th, p * 1.1 - 0.05);
    float slip = (hash(vec2(band, uSeed + 3.0)) - 0.5) * 0.25 * sin(p * 3.14159);
    c = m > 0.5 ? texture(uB, vUv + vec2(slip * (1.0 - p), 0.0)).rgb : texture(uA, vUv + vec2(slip * p, 0.0)).rgb;
  } else if (uType == 32) {    // NEGFLASH: A, then B inverted for a beat-flash, then B
    if (p < 0.5) c = A.rgb;
    else if (p < 0.72) {      // the negative keeps true red (tr.keepRed === 0: all)
      vec3 s = B.rgb; float mx = max(s.r, max(s.g, s.b)), mn = min(s.r, min(s.g, s.b));
      float red = uPar.x * step(max(s.g, s.b), s.r) * smoothstep(0.45, 0.6, (mx - mn) / (mx + 1e-4)) * smoothstep(0.28, 0.4, mx);
      c = mix(vec3(1.0) - s, s, red);
    }
    else c = B.rgb;
  } else if (uType == 33) {    // SEAM: B is sewn on over A along a hand-sewn edge sweeping in direction uPar.xy
                               // (default left->right); a running stitch in uCol rides just inside B, a fold shadow under it
    vec2 n = dot(uPar.xy, uPar.xy) > 0.0 ? normalize(uPar.xy) : vec2(1.0, 0.0);
    vec2 q = (vUv - 0.5) * asp;
    float d = dot(q, n), s = dot(q, vec2(-n.y, n.x));
    float span = 0.5 * (abs(n.x) * 1.7778 + abs(n.y)) + 0.06;
    float front = mix(-span, span, p);
    float e = d - front - (vnoise(vec2(s * 7.0, uSeed)) - 0.5) * 0.016;     // hand-sewn: never a ruler line
    float m = step(e, 0.0);
    c = mix(A.rgb, B.rgb, m);
    c *= 1.0 - 0.32 * m * smoothstep(-0.028, 0.0, e);                        // the fold: B's edge turns under
    c *= 1.0 - 0.22 * (1.0 - m) * smoothstep(0.02, 0.0, e);                  // B's shadow falls on A
    float ph = fract(s / 0.05 + uSeed * 0.37);
    float dash = smoothstep(0.02, 0.06, ph) * smoothstep(0.66, 0.6, ph);     // stitch 60% / gap 40%
    float th = dash * smoothstep(0.0055, 0.0025, abs(e + 0.016));
    c = mix(c, uCol, th * step(0.001, p) * step(p, 0.999));
  } else if (uType == 34) {    // PATCH: B arrives as a patch sewn on at uAt -- a turned, rounded, frayed rectangle
                               // grows to cover the frame, its border running-stitched in uCol
    float k = smoothstep(0.0, 1.0, p);
    float ang = (hash(vec2(uSeed, 3.1)) - 0.5) * 0.3 * (1.0 - k);
    vec2 q = (vUv - uAt) * asp;
    q = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * q;
    vec2 hs = mix(vec2(0.03, 0.022), vec2(2.4, 1.5), k * k);
    float r = 0.025;
    vec2 dd = abs(q) - hs + r;
    float sd = length(max(dd, 0.0)) + min(max(dd.x, dd.y), 0.0) - r;
    sd += (vnoise(q * 40.0 + uSeed) - 0.5) * 0.007;                          // a little fray
    float m = smoothstep(0.0015, -0.0015, sd);
    c = mix(A.rgb, B.rgb, m);
    c *= 1.0 - 0.28 * (1.0 - m) * smoothstep(0.025, 0.0, sd);                // the patch's shadow on A
    float along = abs(q.x) / hs.x > abs(q.y) / hs.y ? q.y : q.x;             // run the dashes along the nearest edge
    float ph = fract(along / 0.042 + uSeed * 0.5);
    float dash = smoothstep(0.02, 0.07, ph) * smoothstep(0.64, 0.58, ph);
    float th = dash * smoothstep(0.0045, 0.002, abs(sd + 0.017));
    c = mix(c, uCol, th * step(0.001, p) * step(p, 0.999));
  } else if (uType == 35) {    // CLOCK: a clock hand sweeps B in around uAt, from 12 o'clock (uPar.x -1 = counter-clockwise: time running back)
    vec2 q = (vUv - uAt) * asp;
    float a = atan(q.x, q.y);                          // 0 at 12 o'clock, +pi/2 at 3 o'clock (GL y up)
    float dir = uPar.x < 0.0 ? -1.0 : 1.0;
    float ang = mod(dir * a, 6.28318) / 6.28318;       // 0..1 around the dial in the sweep direction
    float m = step(ang, p);
    c = mix(A.rgb, B.rgb, m);
    float hand = smoothstep(0.012, 0.0, abs(ang - p) * length(q) * 6.28318) * step(0.001, p) * step(p, 0.999);
    c = mix(c, uCol, hand);
  } else if (uType == 36) {    // SHUTTER: bars close to uCol (top+bottom; uPar.x 1 = left+right), then open on B
    float k = p < 0.5 ? p * 2.0 : (1.0 - p) * 2.0;
    float x = uPar.x > 0.5 ? vUv.x : vUv.y;
    float h = 0.5 * smoothstep(0.0, 1.0, k);
    float m = step(x, h) + step(1.0 - h, x);
    c = mix(p < 0.5 ? A.rgb : B.rgb, uCol, clamp(m, 0.0, 1.0));
  } else if (uType == 37) {    // JIGSAW: B assembles over A as jigsaw pieces (uPar.xy = cols, rows; default
                               // 16 x 9). Each piece lands at its own moment (a hash order), with a white rim (the lock) and a
                               // flash; the seams of landed pieces show faintly and fade out, so p = 1 is exactly B.
    vec2 nc = uPar.x > 0.0 ? uPar.xy : vec2(16.0, 9.0);
    vec2 P = vec2(vUv.x, 1.0 - vUv.y) * nc;            // piece space, y down (row 0 at the top)
    vec2 own = jigOwner(P, nc, uSeed);
    float ord = hash(own + uSeed * 0.37);               // 0..1: when this piece lands
    float land = ord * 0.8;                             // the last piece lands at p = 0.8, then pops for 0.2
    float k = clamp((p - land) / 0.2, 0.0, 1.0);
    float m = step(0.001, k);
    vec2 px = 1.5 / vec2(1920.0, 1080.0) * nc;          // seam: the owner changes within ~1.5 px
    float seam = 0.0;
    if (jigOwner(P + vec2(px.x, 0.0), nc, uSeed) != own) seam = 1.0;
    if (jigOwner(P - vec2(px.x, 0.0), nc, uSeed) != own) seam = 1.0;
    if (jigOwner(P + vec2(0.0, px.y), nc, uSeed) != own) seam = 1.0;
    if (jigOwner(P - vec2(0.0, px.y), nc, uSeed) != own) seam = 1.0;
    c = mix(A.rgb, B.rgb, m);
    c = mix(c, uCol, seam * m * (1.0 - smoothstep(0.0, 1.0, k)));          // the lock: a white rim as it lands
    c *= 1.0 - seam * m * 0.18 * (1.0 - smoothstep(0.85, 1.0, p));       // the seams fade out by p = 1
    c = mix(c, vec3(1.0), 0.35 * m * (1.0 - smoothstep(0.0, 0.35, k)));  // a flash as each piece lands
    if (p >= 1.0) c = B.rgb;
  } else if (uType == 38) {    // SHATTER (a glass break): cracks run out from uAt (p 0-0.12), then A's
                               // shards fly outward, spin and fall, B behind. uPar.x = shards per frame height (default 7);
                               // uCol = the crack / edge glint (white by default; tr.color)
    float n = uPar.x > 0.0 ? uPar.x : 7.0;
    vec2 Q = (vUv - 0.5) * asp * n, Ac = (uAt - 0.5) * asp * n;
    float crack = smoothstep(0.0, 0.12, p), e = clamp((p - 0.12) / 0.88, 0.0, 1.0);
    float s = pow(e, 1.35) * 2.6, drop = 1.1 * n * e * e;
    vec2 X0 = Ac + (Q + vec2(0.0, drop) - Ac) / (1.0 + s), b0 = floor(X0);
    bool hit = false; vec3 col = B.rgb;
    for (int j = -2; j <= 2; j++) {
      for (int i = -2; i <= 2; i++) {
        if (hit) break;
        vec2 cell = b0 + vec2(float(i), float(j)), C = shSeed(cell);
        float k = 0.65 + 0.7 * hash(cell + 3.1), r = (hash(cell + 7.7) - 0.5) * 3.0 * s / 2.6;
        vec2 Cp = Ac + (C - Ac) * (1.0 + s * k) - vec2(0.0, drop * (0.8 + 0.4 * hash(cell + 5.3)));
        vec2 d = Q - Cp; float cs = cos(-r), sn = sin(-r);
        vec2 q0 = vec2(cs * d.x - sn * d.y, sn * d.x + cs * d.y) + C;
        vec3 nn = shNear(q0);
        vec2 uv0 = q0 / n / asp + 0.5;
        if (nn.x == cell.x && nn.y == cell.y && uv0.x >= 0.0 && uv0.x <= 1.0 && uv0.y >= 0.0 && uv0.y <= 1.0) {
          hit = true;
          col = texture(uA, uv0).rgb * mix(1.0, 0.86 + 0.28 * hash(cell + 9.9), crack);
          float reach = length(C - Ac) / (n * 1.3);
          float edge = 1.0 - smoothstep(0.0, 0.03 + 0.03 * s, nn.z);
          col = mix(col, uCol, edge * step(reach, crack * 1.5) * (0.85 - 0.35 * e));
        }
      }
    }
    c = hit ? col : B.rgb;
    c = mix(c, vec3(1.0), 0.5 * (1.0 - smoothstep(0.0, 0.1, abs(p - 0.12))));   // the break flashes
    if (p >= 1.0) c = B.rgb;
  } else {
    c = p < 0.5 ? A.rgb : B.rgb;
  }
  o = vec4(c, 1.0);
}`;

  const FS_POST = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uSrc;
uniform float uGrain, uCA, uFlash, uFrame, uVig, uZoom, uRot;
uniform vec3 uFlashCol; uniform vec2 uShake, uZoomAt, uReg;
${NOISE}
void main(){
  vec2 uv = vUv;
  // punch zoom + rotation + shake (screen space)
  vec2 q = (uv - uZoomAt) * vec2(1.7778, 1.0);
  float cr = cos(uRot), sr = sin(uRot); q = mat2(cr, -sr, sr, cr) * q;
  uv = uZoomAt + q / vec2(1.7778, 1.0) / uZoom + uShake / vec2(1920.0, 1080.0);
  vec2 d = (uv - 0.5); float r2 = dot(d, d);
  vec2 off = d * uCA * (0.25 + r2) / vec2(1920.0, 1080.0) * 4.0;
  // registration: green and red+blue printed uReg px out of register (0 here: it lives in the look pass, per shot)
  vec2 rg = uReg / vec2(1920.0, 1080.0);
  vec3 c = vec3(texture(uSrc, uv + off - rg).r, texture(uSrc, uv + rg).g, texture(uSrc, uv - off - rg).b);
  if (uVig > 0.0) c *= 1.0 - uVig * smoothstep(0.3, 0.95, length(d * vec2(1.3, 1.0)));
  c = mix(c, uFlashCol, clamp(uFlash, 0.0, 1.0));
  // film grain (luminance, deterministic per frame)
  float g = hash(vUv * vec2(1920.0, 1080.0) * 0.5 + fract(uFrame * 0.6180339) * 97.0) - 0.5;
  c += g * uGrain * (0.6 + 0.4 * (1.0 - lum(c)));
  o = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

  function compile(fs) {
    const mk = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) + '\n' + src.split('\n').map((l, i) => (i + 1) + ': ' + l).join('\n').slice(0, 4000)); return s; };
    const p = gl.createProgram();
    gl.attachShader(p, mk(gl.VERTEX_SHADER, VS)); gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs));
    gl.bindAttribLocation(p, 0, 'aPos'); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    p.u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i); p.u[info.name] = gl.getUniformLocation(p, info.name); }
    return p;
  }
  function mkTex() {
    const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  function mkFB() {
    const tex = mkTex(); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, W, H, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { fb, tex };
  }
  DT.initGL = function (canvas) {
    glCanvas = canvas; canvas.width = W; canvas.height = H;
    gl = canvas.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false, premultipliedAlpha: false, alpha: false });
    if (!gl || gl.isContextLost()) throw new Error('WebGL2 unavailable (or lost at start): see the kit MACHINE.md, browser flags');
    // a context lost mid-render leaves every later frame BLANK: fail loudly instead (render/browser.mjs picks flags
    // that work; a machine whose GPU path dies falls back to software WebGL there)
    canvas.addEventListener('webglcontextlost', (e) => {
      e.preventDefault();
      window.DT_fatal = 'WebGL context lost: frames would be blank (see MACHINE.md: the browser flags)';
    });
    quad = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    progFX = compile(FS_FX); progTR = compile(FS_TR); progPost = compile(FS_POST);
    texBase = mkTex(); texOver = mkTex();
    fbs = [mkFB(), mkFB()]; fbOut = mkFB();
    DT.gl = gl;
  };
  function draw(prog, target) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.fb : null);
    gl.viewport(0, 0, W, H);
    gl.useProgram(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, quad); gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
  function upload(tex, canvas, premult) {
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, !!premult);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
  }
  const col = (c, d) => (Array.isArray(c) ? c : hexToRgb(c || d));

  // ---------------------------------------------------------------- the look (defaults)
  const LOOK0 = { cold: 0, coldColor: DT.pal.ink, warm: 0, warmColor: DT.pal.blush, warmAt: [0.5, 0.55],
    halftone: 0, halftoneSize: 9, halftoneAngle: 0.6, halftoneInk: '#1b1520', duotone: 0, duoDark: DT.pal.ink, duoLight: DT.pal.white,
    invert: 0, impact: 0, impactRed: 0, vignette: 0, posterize: 0, sat: 1, bright: 1,
    // post (the frame, not the shot): taken from the shot on screen (the incoming one during a transition)
    grain: 0.025, ca: 0, flash: 0, flashColor: '#ffffff', shake: [0, 0], zoom: 1, zoomAt: [0.5, 0.5], rot: 0, postVignette: 0,
    // the film stock and the tricks (no halation by default)
    grade: '#ffffff', gradeAmt: 0, halation: 0, leak: 0, leakAt: [0.92, 0.15], leakColor: '#ff6a1a',
    vhs: 0, vhsRoll: 1, ripple: 0, rippleFreq: 40, swirl: 0, swirlAt: [0.5, 0.5], hue: 0,
    linen: 0, paper: 0,      // a cloth emboss and a paper tooth: off by default (painters may use them for texture)
    blur: 0, blurDir: [1, 0], radial: 0, radialAt: [0.5, 0.5],
    // registration (a number = px along regAng; [x, y] = a px vector; null = ctx.reg + a kick pulse scaled by
    // 1 - ctx.merge), the seam (px; 0 = none), glitch slices, CRT phosphor, 1-bit mono
    reg: 0, regAng: 0, regKick: 5, regOver: 0.5,   // registration OFF by default (set look.reg for a hit)   // regOver: the share of the registration the OVER layer gets (HUD/labels stay legible)
    seam: 0, seamAt: [0.5, 0.5], seamAng: 0, seamColor: '#040406',
    glitch: 0, scan: 0, mono: 0, monoLevel: 0.5, monoDark: '#040406', monoLight: '#f4f7f2',
    // RED INK (keepRed 0..1; keepLevel = the ink/paper threshold on luminance; keepSoft = its edge)
    keepRed: 0, keepLevel: 0.45, keepSoft: 0.07, keepInk: '#1b1a1f', keepPaper: '#f6f1e7', keepRedCol: '#d11f2f',
    // the palette grade (0 = off; spread DT.GRADES.<name> into your look) + the red-keeping invert
    gmap: 0, gmapStops: ['#080608', '#2e160e', '#ec6816', '#ffe2b0'], gmapPos: [0, 0.28, 0.62, 1], gmapKeepRed: 1,
    invertKeepRed: 0 };
  // named reel palettes for look.gmap ({gmapStops, gmapPos}); a film's vocab adds its own, picked from the film's own
  // pictures (its storyboard's colour script).
  DT.GRADES = DT.GRADES || {};
  DT.LOOK0 = LOOK0;
  // the registration vector (px) for a look + ctx: the green plate and the red+blue plate, out of register
  DT.regVec = function (look, ctx) {
    if (Array.isArray(look.reg)) return look.reg;
    let r = look.reg != null ? look.reg : ctx.reg + (look.regKick || 0) * ctx.kick * clamp(1 - ctx.merge);
    const a = look.regAng + (look.reg == null ? 0.35 * Math.sin(ctx.t * 0.9) : 0);   // the plates drift, alive
    return [r * Math.cos(a), r * Math.sin(a)];
  };

  // render one shot at time t into fbs[slot]; returns its look
  function renderShot(shot, t, tc, slot) {
    const sc = DT.scenes[shot.scene] || DT.scenes.__missing;
    const ctx = makeCtx(shot, t, tc);
    gBase.setTransform(1, 0, 0, 1, 0, 0); gBase.globalAlpha = 1; gBase.globalCompositeOperation = 'source-over'; gBase.filter = 'none';
    gBase.fillStyle = (sc.bg && (typeof sc.bg === 'function' ? sc.bg(ctx) : sc.bg)) || DT.pal.void;
    gBase.fillRect(0, 0, W, H);
    gBase.save(); sc.draw && sc.draw(gBase, ctx); gBase.restore();
    gOver.setTransform(1, 0, 0, 1, 0, 0); gOver.globalAlpha = 1; gOver.globalCompositeOperation = 'source-over'; gOver.filter = 'none';
    gOver.clearRect(0, 0, W, H);
    if (sc.over) { gOver.save(); sc.over(gOver, ctx); gOver.restore(); }
    const look = Object.assign({}, LOOK0, sc.look ? sc.look(ctx) : {}, shot.look || {});
    upload(texBase, cvBase, false); upload(texOver, cvOver, true);
    const p = progFX; gl.useProgram(p);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texBase); gl.uniform1i(p.u.uBase, 0);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texOver); gl.uniform1i(p.u.uOver, 1);
    gl.uniform1f(p.u.uCold, look.cold); gl.uniform3fv(p.u.uColdCol, col(look.coldColor));
    gl.uniform1f(p.u.uWarm, look.warm); gl.uniform3fv(p.u.uWarmCol, col(look.warmColor)); gl.uniform2fv(p.u.uWarmAt, [look.warmAt[0], 1 - look.warmAt[1]]);
    gl.uniform1f(p.u.uHalf, look.halftone); gl.uniform1f(p.u.uHalfSize, look.halftoneSize); gl.uniform1f(p.u.uHalfAng, look.halftoneAngle); gl.uniform3fv(p.u.uHalfInk, col(look.halftoneInk));
    gl.uniform1f(p.u.uDuo, look.duotone); gl.uniform3fv(p.u.uDuoDark, col(look.duoDark)); gl.uniform3fv(p.u.uDuoLight, col(look.duoLight));
    gl.uniform1f(p.u.uInvert, look.invert); gl.uniform1f(p.u.uImpact, look.impact); gl.uniform1f(p.u.uImpactRed, look.impactRed || 0); gl.uniform1f(p.u.uVig, look.vignette);
    gl.uniform1f(p.u.uPosterize, look.posterize); gl.uniform1f(p.u.uSat, look.sat); gl.uniform1f(p.u.uBright, look.bright);
    gl.uniform1f(p.u.uSeed, (shot.seed % 1000) / 37.0);
    gl.uniform1f(p.u.uTime, t); gl.uniform3fv(p.u.uGrade, col(look.grade)); gl.uniform1f(p.u.uGradeAmt, look.gradeAmt);
    gl.uniform1f(p.u.uHal, look.halation); gl.uniform1f(p.u.uLeak, look.leak); gl.uniform2fv(p.u.uLeakAt, [look.leakAt[0], 1 - look.leakAt[1]]);
    gl.uniform3fv(p.u.uLeakCol, col(look.leakColor)); gl.uniform1f(p.u.uVhs, look.vhs); gl.uniform1f(p.u.uVhsRoll, look.vhsRoll);
    gl.uniform1f(p.u.uRipple, look.ripple); gl.uniform1f(p.u.uRippleF, look.rippleFreq); gl.uniform1f(p.u.uSwirl, look.swirl);
    gl.uniform2fv(p.u.uSwirlAt, [look.swirlAt[0], 1 - look.swirlAt[1]]); gl.uniform1f(p.u.uHue, look.hue);
    gl.uniform1f(p.u.uLinen, look.linen); gl.uniform1f(p.u.uPaper, look.paper);
    { const d = look.blurDir, n = Math.hypot(d[0], d[1]) || 1; gl.uniform1f(p.u.uMBlur, look.blur); gl.uniform2fv(p.u.uMDir, [d[0] / n, -d[1] / n]); }
    gl.uniform1f(p.u.uRBlur, look.radial); gl.uniform2fv(p.u.uRAt, [look.radialAt[0], 1 - look.radialAt[1]]);
    gl.uniform1f(p.u.uSeam, look.seam || 0); gl.uniform2fv(p.u.uSeamAt, [look.seamAt[0], 1 - look.seamAt[1]]);
    gl.uniform1f(p.u.uSeamAng, -(look.seamAng || 0)); gl.uniform3fv(p.u.uSeamCol, col(look.seamColor));
    gl.uniform1f(p.u.uGlitch, look.glitch || 0); gl.uniform1f(p.u.uScan, look.scan || 0); gl.uniform1f(p.u.uFrameN, Math.round(t * DT.FPS));
    gl.uniform1f(p.u.uMono, look.mono || 0); gl.uniform1f(p.u.uMonoLevel, look.monoLevel);
    gl.uniform1f(p.u.uKeepRed, look.keepRed || 0); gl.uniform1f(p.u.uKeepLevel, look.keepLevel); gl.uniform1f(p.u.uKeepSoft, look.keepSoft);
    gl.uniform3fv(p.u.uKeepInk, col(look.keepInk)); gl.uniform3fv(p.u.uKeepPaper, col(look.keepPaper)); gl.uniform3fv(p.u.uKeepRedCol, col(look.keepRedCol));
    { const st = look.gmapStops, gp = look.gmapPos;   // the palette grade
      gl.uniform1f(p.u.uGmap, look.gmap || 0); gl.uniform1f(p.u.uGmapKeepRed, look.gmapKeepRed == null ? 1 : look.gmapKeepRed);
      gl.uniform3fv(p.u.uG0, col(st[0])); gl.uniform3fv(p.u.uG1, col(st[1])); gl.uniform3fv(p.u.uG2, col(st[2])); gl.uniform3fv(p.u.uG3, col(st[3]));
      gl.uniform4fv(p.u.uGpos, gp); }
    gl.uniform1f(p.u.uInvertKeepRed, look.invertKeepRed || 0);
    gl.uniform3fv(p.u.uMonoDark, col(look.monoDark)); gl.uniform3fv(p.u.uMonoLight, col(look.monoLight));
    { const r = DT.regVec(look, ctx); gl.uniform2fv(p.u.uReg, [r[0], -r[1]]); gl.uniform1f(p.u.uRegOver, look.regOver != null ? look.regOver : 0.5); }
    draw(p, fbs[slot]);
    return { look, ctx };
  }

  const TR_TYPES = { cut: 0, dissolve: 1, dip: 2, flash: 3, ink: 4, blush: 5, heart: 6, slash: 7, wipe: 8, tear: 9, blink: 10, zoom: 11, glitch: 12, circle: 13, blinds: 14, mosaic: 15, split: 16, checker: 17,
    wave: 18, tide: 19, ripple: 20, spin: 21, leak: 22, film: 23, page: 24, star: 25, whip: 26, irisdip: 27,
    merge: 28, reg: 29, static: 30, slices: 31, negflash: 32, seam: 33, patch: 34, clock: 35, shutter: 36, jigsaw: 37, shatter: 38 };
  const TR_COL = { dip: '#0b1a3a', flash: '#ffffff', ink: '#14213d', blush: '#ff9fae', heart: '#ffffff', slash: '#ffffff', tear: '#fff6e6', blink: '#0e0b10', circle: '#ffffff',
    wave: '#1aa7c9', tide: '#1d8fb3', spin: '#12253d', leak: '#ff6a1a', film: '#0b0b0b', page: '#fff6e6', star: '#ffffff', irisdip: '#000000',
    merge: '#8cff1a', seam: '#d6364b', patch: '#f3efe2', clock: '#f3efe6', shutter: '#0a0a0c', jigsaw: '#ffffff', shatter: '#ffffff',
    tear: '#f6f1e7' };

  // ---------------------------------------------------------------- one frame
  DT.frameInfo = null;
  DT.renderFrame = async function (n) {
    if (gl && gl.isContextLost()) throw new Error('WebGL context lost: frame ' + n + ' would be blank (see MACHINE.md: the browser flags)');
    const t = n / DT.FPS;
    const i = shotIndexAt(t);
    const cur = DT.shots[i], nxt = DT.shots[i + 1];
    // are we inside a transition window? (either the current shot's own incoming window, or the next's)
    let A = null, B = null, p = 0, tr = null;
    if (cur.tr.dur > 0 && t < cur.tr.t1 && DT.shots[i - 1]) { A = DT.shots[i - 1]; B = cur; tr = cur.tr; }
    else if (nxt && nxt.tr.dur > 0 && t >= nxt.tr.t0) { A = cur; B = nxt; tr = nxt.tr; }
    const need = new Set();
    const collect = (s) => {
      const sc = DT.scenes[s.scene]; if (!sc || !sc.assets) return;
      const list = typeof sc.assets === 'function' ? sc.assets(makeCtx(s, t, t)) : sc.assets;
      for (const k of list || []) if (k) need.add(k);
    };
    if (tr) { collect(A); collect(B); } else collect(cur);
    await Promise.all([...need].map((k) => DT.load(k)));
    evict();
    let look, ctx, info;
    if (tr) {
      p = clamp((t - tr.t0) / Math.max(1e-6, tr.t1 - tr.t0));
      const ra = renderShot(A, t, t, 0), rb = renderShot(B, t, t, 1);
      const pr = progTR; gl.useProgram(pr);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, fbs[0].tex); gl.uniform1i(pr.u.uA, 0);
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, fbs[1].tex); gl.uniform1i(pr.u.uB, 1);
      gl.uniform1i(pr.u.uType, TR_TYPES[tr.type] != null ? TR_TYPES[tr.type] : 1);
      const ease0 = tr.ease ? ease[tr.ease] : (x) => x;
      gl.uniform1f(pr.u.uP, ease0(p)); gl.uniform1f(pr.u.uSeed, (B.seed % 1000) / 41.0);
      gl.uniform4fv(pr.u.uPar, tr.par || [tr.angle != null ? tr.angle : -0.9, 0, 0, 0]);
      gl.uniform3fv(pr.u.uCol, col(tr.color || TR_COL[tr.type] || '#ffffff'));
      const at = tr.at || [0.5, 0.5]; gl.uniform2fv(pr.u.uAt, [at[0], 1 - at[1]]);
      if (tr.type === 'wipe') gl.uniform4fv(pr.u.uPar, tr.par || [1, 0, 0, 0]);
      if (tr.type === 'blinds') gl.uniform4fv(pr.u.uPar, tr.par || [9, 0, 0, 0]);
      if (tr.type === 'wave' || tr.type === 'spin' || tr.type === 'film' || tr.type === 'whip') gl.uniform4fv(pr.u.uPar, tr.par || [tr.dir != null ? tr.dir : 1, 0, 0, 0]);
      if (tr.type === 'clock') gl.uniform4fv(pr.u.uPar, tr.par || [tr.dir != null ? tr.dir : 1, 0, 0, 0]);
      if (tr.type === 'shutter') gl.uniform4fv(pr.u.uPar, tr.par || [tr.sides ? 1 : 0, 0, 0, 0]);
      if (tr.type === 'jigsaw') gl.uniform4fv(pr.u.uPar, tr.par || [tr.cols || 16, tr.rows || 9, 0, 0]);
      if (tr.type === 'shatter') gl.uniform4fv(pr.u.uPar, tr.par || [tr.cells || 7, 0, 0, 0]);
      if (tr.type === 'negflash') gl.uniform4fv(pr.u.uPar, tr.par || [tr.keepRed === 0 ? 0 : 1, 0, 0, 0]);
      if (tr.type === 'merge') gl.uniform4fv(pr.u.uPar, tr.par || [tr.horizontal ? 1 : 0, 0, 0, 0]);
      if (tr.type === 'reg') gl.uniform4fv(pr.u.uPar, tr.par || [tr.angle != null ? tr.angle : 0, 0, 0, 0]);
      if (tr.type === 'slices') gl.uniform4fv(pr.u.uPar, tr.par || [tr.bands || 18, 0, 0, 0]);
      // seam: {dx, dy} in SCREEN terms (dx 1 = left->right, the default; dy 1 = top->bottom)
      if (tr.type === 'seam') gl.uniform4fv(pr.u.uPar, tr.par || [tr.dx != null ? tr.dx : (tr.dy ? 0 : 1), -(tr.dy || 0), 0, 0]);   // dy alone = vertical
      draw(pr, fbOut);
      look = p < 0.5 ? ra.look : rb.look; ctx = p < 0.5 ? ra.ctx : rb.ctx;
      info = { shot: B.id, from: A.id, transition: tr.type, p: +p.toFixed(2) };
    } else {
      const r = renderShot(cur, t, t, 0);
      look = r.look; ctx = r.ctx; info = { shot: cur.id };
    }
    // post
    const pp = progPost; gl.useProgram(pp);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tr ? fbOut.tex : fbs[0].tex); gl.uniform1i(pp.u.uSrc, 0);
    gl.uniform1f(pp.u.uGrain, look.grain); gl.uniform1f(pp.u.uCA, look.ca); gl.uniform1f(pp.u.uFlash, look.flash);
    gl.uniform3fv(pp.u.uFlashCol, col(look.flashColor)); gl.uniform1f(pp.u.uFrame, n); gl.uniform1f(pp.u.uVig, look.postVignette);
    gl.uniform2fv(pp.u.uShake, [look.shake[0], -look.shake[1]]); gl.uniform1f(pp.u.uZoom, look.zoom || 1);
    gl.uniform2fv(pp.u.uZoomAt, [look.zoomAt[0], 1 - look.zoomAt[1]]); gl.uniform1f(pp.u.uRot, look.rot || 0);
    { const r = DT.regVec(look, ctx); gl.uniform2fv(pp.u.uReg, [0, 0]); info && (info.reg = +Math.hypot(r[0], r[1]).toFixed(1)); }   // registration now lives in the look pass (per shot)
    draw(pp, null);
    info.t = +t.toFixed(3); info.frame = n;
    DT.frameInfo = info;
    return info;
  };

  // a scene that doesn't exist yet renders as an animatic card (never in strict mode)
  DT.scene('__missing', {
    bg: '#050805',
    draw(g, ctx) {
      g.fillStyle = '#9dff5c'; g.font = '64px "DotGothic16"'; g.textAlign = 'center';
      g.fillText(ctx.shot.scene + ' (not painted yet)', W / 2, H / 2 - 20);
      g.font = '36px "Space Mono"'; g.fillText(ctx.shot.id + '   ' + ctx.t.toFixed(2) + 's', W / 2, H / 2 + 50);
      const L = ctx.lineNow(); if (L) { g.fillStyle = '#f4f7f2'; g.fillText('(' + String(L.text || L.gist || '').slice(0, 70) + ')', W / 2, H / 2 + 130);   /* some timings carry a gist instead of the words */ }
      const sec = (DT.timing.sections || []).find((S) => ctx.t >= S.start && ctx.t < S.end);
      g.fillStyle = '#f2a23a'; g.font = '30px "Space Mono"';
      if (sec) g.fillText(sec.name + ': ' + String(sec.story).slice(0, 90), W / 2, H / 2 + 200);
    },
  });
})();
