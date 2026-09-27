// =============================================================================
// kit.js -- the pop vocabulary (Canvas2D). Every function takes the 2D context `g` first.
// Deterministic: anything random takes a seed (use ctx.rnd / ctx.jit / ctx.drawing), never Math.random.
//
//   TYPE     K.F (font names) · K.text · K.fit · K.typeOn · K.slam · K.inner (an inner-voice scrawl) · K.lyric
//   MARKER   K.marker · K.scribble · K.loop · K.arrow · K.xmark · K.underline · K.rc(g) (rough.js)
//   SHAPES   K.heart · K.star · K.sparkle · K.burst · K.rays · K.bubble · K.knife · K.carrot · K.bunny
//            K.tag · K.stamp · K.barcode · K.seal (想) · K.label · K.callout · K.grawlix
//   PATTERN  K.stripes · K.dots · K.checker · K.speedLines · K.halftone · K.confetti · K.grid
//   IMAGES   K.img (cut-outs, anchored by their alpha bbox) · K.sticker (white die-cut border) · K.sil (solid
//            silhouette) · K.duo (duotone sprite) · K.map (image px -> screen) · K.eyes
//   MOTION   K.cam · K.shake · K.pop (scale-in) · K.wob (boil)
// =============================================================================
(function () {
  'use strict';
  const DT = window.DT, U = DT.util, W = DT.W, H = DT.H;
  const K = (DT.K = {});
  const TAU = Math.PI * 2;

  // ---------------------------------------------------------------- fonts
  K.F = {
    display: 'Dela Gothic One',     // outside voice: big, heavy, pop (JP-MV energy)
    cond: 'Anton',                  // labels, UI, headlines
    marker: 'Caveat Brush',         // an inner voice (scrawl)
    marker2: 'Permanent Marker',    // louder scrawl, stamps
    scrawl: 'Reenie Beanie',        // tiny nervous handwriting
    mono: 'Space Mono',             // data, forms, readouts
    serif: 'DM Serif Display',      // field guide, contracts, the whisper
    pop: 'Mochiy Pop One',          // cute rounded pop
    cjk: 'Ma Shan Zheng',           // brush calligraphy (想)
    block: 'Rubik Mono One',        // chunky UI
    bungee: 'Bungee',               // signage / game UI
    script: 'Shrikhand',            // retro ad script (propaganda posters)
  };

  // ---------------------------------------------------------------- type
  // K.text(g, str, x, y, {font, size, color, align, baseline, stroke, strokeW, tracking, rot, skew, shadow, alpha, italic})
  K.text = function (g, str, x, y, o = {}) {
    g.save();
    g.translate(x, y);
    if (o.rot) g.rotate(o.rot);
    if (o.skew) g.transform(1, 0, o.skew, 1, 0, 0);
    if (o.scale) g.scale(o.scale, o.scale);
    g.font = `${o.italic ? 'italic ' : ''}${o.weight || ''} ${o.size || 64}px "${o.font || K.F.display}"`;
    g.textAlign = o.align || 'center';
    g.textBaseline = o.baseline || 'alphabetic';
    g.letterSpacing = (o.tracking || 0) + 'px';
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    if (o.shadow) { g.fillStyle = o.shadow; g.fillText(str, o.shadowX != null ? o.shadowX : 8, o.shadowY != null ? o.shadowY : 8); }
    if (o.stroke) { g.lineJoin = 'round'; g.lineWidth = o.strokeW || 10; g.strokeStyle = o.stroke; g.strokeText(str, 0, 0); }
    g.fillStyle = o.color || DT.pal.ink;
    g.fillText(str, 0, 0);
    g.restore();
  };
  K.measure = function (g, str, o = {}) {
    g.save(); g.font = `${o.size || 64}px "${o.font || K.F.display}"`; g.letterSpacing = (o.tracking || 0) + 'px';
    const m = g.measureText(str); g.restore(); return m.width;
  };
  // size so that `str` fits width w (capped at max)
  K.fit = (g, str, w, o = {}) => Math.min(o.max || 400, (o.size || 100) * w / Math.max(1, K.measure(g, str, { ...o, size: o.size || 100 })));
  // typewriter reveal: progress 0..1 (by characters)
  K.typeOn = function (g, str, x, y, p, o = {}) { const n = Math.floor(U.clamp(p) * str.length + 1e-6); K.text(g, str.slice(0, n), x, y, { align: 'left', ...o }); };
  // slam: the word arrives at age 0 big and settles with a little overshoot. age = seconds since the hit.
  K.slam = function (g, str, x, y, age, o = {}) {
    if (age < 0) return;
    const d = o.dur || 0.22;
    const k = U.clamp(age / d);
    const s = age < d ? U.lerp(o.from || 2.4, 1, U.ease.back(k)) : 1;
    const shake = age < d * 1.5 ? (1 - age / (d * 1.5)) * (o.shake != null ? o.shake : 10) : 0;
    const sx = shake * (U.h01(age * 1000 | 0, 1) - 0.5) * 2, sy = shake * (U.h01(age * 1000 | 0, 2) - 0.5) * 2;
    K.text(g, str, x + sx, y + sy, { ...o, scale: (o.scale || 1) * s });
  };
  // an inner voice: marker scrawl (red by default), each letter wobbles on twos
  K.inner = function (g, str, x, y, o = {}) {
    const size = o.size || 72, drawing = o.drawing || 0, seed = o.seed || 1;
    g.save();
    g.font = `${size}px "${o.font || K.F.marker}"`;
    g.textBaseline = 'alphabetic';
    const total = g.measureText(str).width;
    let cx = o.align === 'left' ? x : o.align === 'right' ? x - total : x - total / 2;
    const n = o.reveal != null ? Math.floor(U.clamp(o.reveal) * str.length + 1e-6) : str.length;
    for (let i = 0; i < n; i++) {
      const ch = str[i], w = g.measureText(ch).width;
      const jx = (U.h01(seed, i, drawing, 3) - 0.5) * size * 0.05, jy = (U.h01(seed, i, drawing, 4) - 0.5) * size * 0.07;
      const r = (U.h01(seed, i, drawing, 5) - 0.5) * 0.12 + (o.rot || 0);
      g.save(); g.translate(cx + w / 2 + jx, y + jy + Math.sin(i * 0.7 + seed) * size * (o.wave || 0)); g.rotate(r);
      if (o.stroke) { g.lineWidth = o.strokeW || size * 0.16; g.lineJoin = 'round'; g.strokeStyle = o.stroke; g.strokeText(ch, -w / 2, 0); }
      g.fillStyle = o.color || DT.pal.red; g.fillText(ch, -w / 2, 0);
      g.restore();
      cx += w;
    }
    g.restore();
    return total;
  };
  // lyric words as they are sung: returns [{w, s, e, age, x}] laid out centred; draws via o.draw(word, x, y, age) or default
  K.lyric = function (g, ctx, n, x, y, o = {}) {
    const L = DT.timing.lines[n]; if (!L) return;
    const size = o.size || 90, font = o.font || K.F.display, gap = size * (o.gap || 0.28);
    g.save(); g.font = `${size}px "${font}"`;
    const words = L.words.map((w) => ({ ...w, text: (o.clean !== false ? w.w.replace(/[()"]/g, '') : w.w), }));
    for (const w of words) w.wd = g.measureText(w.text).width;
    const total = words.reduce((a, w) => a + w.wd, 0) + gap * (words.length - 1);
    let cx = o.align === 'left' ? x : x - total / 2;
    for (const w of words) {
      const age = ctx.t - w.s + (o.lead || 0);
      if (age >= 0 || o.showAll) {
        if (o.draw) o.draw(w, cx, y, age);
        else K.slam(g, w.text, cx + w.wd / 2, y, age, { font, size, color: w.inner ? DT.pal.red : (o.color || DT.pal.ink), stroke: o.stroke, strokeW: o.strokeW, shake: o.shake });
      }
      cx += w.wd + gap;
    }
    g.restore();
    return total;
  };

  // ---------------------------------------------------------------- marker (hand-drawn lines)
  // K.marker(g, pts, {color, w, seed, drawing, jitter, taper, alpha, progress})  pts = [[x,y],...]
  K.marker = function (g, pts, o = {}) {
    if (pts.length < 2) return;
    const seed = o.seed || 1, dr = o.drawing || 0, j = o.jitter != null ? o.jitter : 2.2;
    // resample so every segment is short (smooth wobble), respect progress (draw-on)
    const P = []; for (let i = 0; i < pts.length - 1; i++) {
      const [x0, y0] = pts[i], [x1, y1] = pts[i + 1]; const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 14));
      for (let k = 0; k < n; k++) P.push([U.lerp(x0, x1, k / n), U.lerp(y0, y1, k / n)]);
    }
    P.push(pts[pts.length - 1]);
    const upto = o.progress != null ? Math.max(2, Math.floor(P.length * U.clamp(o.progress))) : P.length;
    g.save();
    g.strokeStyle = o.color || DT.pal.red; g.lineCap = 'round'; g.lineJoin = 'round';
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    const w = o.w || 8;
    for (let i = 1; i < upto; i++) {
      const a = P[i - 1], b = P[i];
      const f = i / P.length;
      const taper = o.taper ? Math.min(1, Math.min(f, 1 - f) * 6 + 0.25) : 1;
      g.lineWidth = w * taper * (0.85 + 0.3 * U.h01(seed, i >> 2, dr));
      g.beginPath();
      g.moveTo(a[0] + (U.h01(seed, i - 1, dr, 1) - 0.5) * j, a[1] + (U.h01(seed, i - 1, dr, 2) - 0.5) * j);
      g.lineTo(b[0] + (U.h01(seed, i, dr, 1) - 0.5) * j, b[1] + (U.h01(seed, i, dr, 2) - 0.5) * j);
      g.stroke();
    }
    g.restore();
  };
  // censor scribble over a box (zig-zag), progress = how much has been scribbled
  K.scribble = function (g, x, y, w, h, o = {}) {
    const n = o.passes || Math.max(4, Math.round(w / (o.step || 26)));
    const pts = []; for (let i = 0; i <= n; i++) { const fx = x + w * i / n; pts.push([fx + (U.h01(o.seed || 3, i) - 0.5) * 18, i % 2 ? y + h : y]); }
    K.marker(g, pts, { w: o.w || 14, color: o.color || DT.pal.red, seed: o.seed, drawing: o.drawing, jitter: 3, progress: o.progress });
  };
  // a loose loop drawn around something (marker circle)
  K.loop = function (g, cx, cy, rx, ry, o = {}) {
    const pts = [], turns = o.turns || 1.15, a0 = o.a0 != null ? o.a0 : -2.2;
    for (let i = 0; i <= 64; i++) { const a = a0 + TAU * turns * i / 64; const wob = 1 + (U.h01(o.seed || 5, i >> 3) - 0.5) * 0.08; pts.push([cx + Math.cos(a) * rx * wob, cy + Math.sin(a) * ry * wob]); }
    K.marker(g, pts, { w: o.w || 8, color: o.color, seed: o.seed, drawing: o.drawing, progress: o.progress, taper: true });
  };
  K.arrow = function (g, x0, y0, x1, y1, o = {}) {
    const mx = (x0 + x1) / 2 + (o.bend || 0) * (y1 - y0) * 0.2, my = (y0 + y1) / 2 - (o.bend || 0) * (x1 - x0) * 0.2;
    const pts = []; for (let i = 0; i <= 20; i++) { const t = i / 20; pts.push([(1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1]); }
    K.marker(g, pts, { w: o.w || 6, color: o.color, seed: o.seed, drawing: o.drawing, progress: o.progress });
    if (o.progress == null || o.progress >= 0.95) {
      const a = Math.atan2(y1 - my, x1 - mx), L = o.head || 26;
      K.marker(g, [[x1 - Math.cos(a - 0.5) * L, y1 - Math.sin(a - 0.5) * L], [x1, y1], [x1 - Math.cos(a + 0.5) * L, y1 - Math.sin(a + 0.5) * L]], { w: o.w || 6, color: o.color, seed: (o.seed || 1) + 9, drawing: o.drawing });
    }
  };
  K.xmark = function (g, cx, cy, r, o = {}) {
    K.marker(g, [[cx - r, cy - r], [cx + r, cy + r]], { w: o.w || 14, color: o.color, seed: o.seed, drawing: o.drawing, progress: o.progress != null ? U.clamp(o.progress * 2) : null });
    if (o.progress == null || o.progress > 0.5) K.marker(g, [[cx + r, cy - r], [cx - r, cy + r]], { w: o.w || 14, color: o.color, seed: (o.seed || 1) + 7, drawing: o.drawing, progress: o.progress != null ? U.clamp(o.progress * 2 - 1) : null });
  };
  K.underline = (g, x0, x1, y, o = {}) => K.marker(g, [[x0, y], [(x0 + x1) / 2, y + (o.sag || 6)], [x1, y - 3]], o);
  // rough.js on the canvas behind g (hachure fills, sketchy shapes). Always pass {seed}.
  const rcs = new WeakMap();
  K.rc = (g) => { let r = rcs.get(g.canvas); if (!r) { r = window.rough.canvas(g.canvas); rcs.set(g.canvas, r); } return r; };

  // ---------------------------------------------------------------- shapes
  function heartPath(g, x, y, s) {
    g.beginPath();
    g.moveTo(x, y + s * 0.32);
    g.bezierCurveTo(x - s * 0.05, y + s * 0.24, x - s * 0.52, y - s * 0.02, x - s * 0.5, y - s * 0.28);
    g.bezierCurveTo(x - s * 0.48, y - s * 0.56, x - s * 0.1, y - s * 0.6, x, y - s * 0.32);
    g.bezierCurveTo(x + s * 0.1, y - s * 0.6, x + s * 0.48, y - s * 0.56, x + s * 0.5, y - s * 0.28);
    g.bezierCurveTo(x + s * 0.52, y - s * 0.02, x + s * 0.05, y + s * 0.24, x, y + s * 0.32);
    g.closePath();
  }
  K.heartPath = heartPath;
  K.heart = function (g, x, y, s, o = {}) {
    g.save(); g.translate(x, y); if (o.rot) g.rotate(o.rot); if (o.alpha != null) g.globalAlpha *= o.alpha;
    heartPath(g, 0, 0, s);
    if (o.fill !== false) { g.fillStyle = o.fill || DT.pal.red; g.fill(); }
    if (o.stroke) { g.lineWidth = o.lw || s * 0.06; g.strokeStyle = o.stroke; g.lineJoin = 'round'; g.stroke(); }
    g.restore();
  };
  K.star = function (g, x, y, r, o = {}) {
    const n = o.points || 5, ri = r * (o.inner || 0.45);
    g.save(); g.translate(x, y); g.rotate(o.rot || 0); g.beginPath();
    for (let i = 0; i < n * 2; i++) { const a = -Math.PI / 2 + i * Math.PI / n, rr = i % 2 ? ri : r; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); }
    g.closePath(); g.fillStyle = o.fill || DT.pal.lemon; g.fill();
    if (o.stroke) { g.lineWidth = o.lw || 6; g.strokeStyle = o.stroke; g.lineJoin = 'round'; g.stroke(); }
    g.restore();
  };
  K.sparkle = function (g, x, y, r, o = {}) {       // 4-point twinkle
    g.save(); g.translate(x, y); g.rotate(o.rot || 0); g.beginPath();
    for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4, rr = i % 2 ? r * 0.16 : r; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); }
    g.closePath(); g.fillStyle = o.fill || '#fff'; g.fill(); g.restore();
  };
  // comic explosion
  K.burst = function (g, x, y, r, o = {}) {
    const n = o.spikes || 18, seed = o.seed || 7;
    g.save(); g.translate(x, y); g.rotate(o.rot || 0); g.beginPath();
    for (let i = 0; i < n * 2; i++) {
      const a = i * Math.PI / n, jag = 1 + (U.h01(seed, i, o.drawing || 0) - 0.5) * (o.jag != null ? o.jag : 0.35);
      const rr = (i % 2 ? r * (o.inner || 0.68) : r) * jag; g.lineTo(Math.cos(a) * rr * (o.sx || 1), Math.sin(a) * rr);
    }
    g.closePath();
    if (o.fill !== false) { g.fillStyle = o.fill || DT.pal.lemon; g.fill(); }
    if (o.stroke) { g.lineWidth = o.lw || 10; g.strokeStyle = o.stroke; g.lineJoin = 'miter'; g.stroke(); }
    g.restore();
  };
  // sunburst rays from (x,y) covering the whole frame
  K.rays = function (g, x, y, o = {}) {
    const n = o.n || 24, R = 3000, rot = o.rot || 0;
    g.save(); g.fillStyle = o.a || DT.pal.pink; g.fillRect(0, 0, W, H); g.fillStyle = o.b || DT.pal.hotpink;
    for (let i = 0; i < n; i++) {
      const a0 = rot + i * TAU / n, a1 = a0 + TAU / n * (o.duty || 0.5);
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a0) * R, y + Math.sin(a0) * R); g.lineTo(x + Math.cos(a1) * R, y + Math.sin(a1) * R); g.closePath(); g.fill();
    }
    g.restore();
  };
  // balloons: kind 'speech' | 'thought' | 'shout' | 'whisper'
  K.bubble = function (g, x, y, w, h, o = {}) {
    const kind = o.kind || 'speech', fill = o.fill || '#fff', stroke = o.stroke || DT.pal.ink, lw = o.lw || 6, seed = o.seed || 11;
    g.save(); g.lineWidth = lw; g.strokeStyle = stroke; g.fillStyle = fill; g.lineJoin = 'round';
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    if (kind === 'thought') {
      // cloud: bumps around an ellipse, then trailing puffs toward the tail
      const n = o.bumps || 11; g.beginPath();
      for (let i = 0; i <= n; i++) {
        const a0 = i * TAU / n, a1 = (i + 1) * TAU / n, am = (a0 + a1) / 2;
        const p0 = [x + Math.cos(a0) * w / 2, y + Math.sin(a0) * h / 2], p1 = [x + Math.cos(a1) * w / 2, y + Math.sin(a1) * h / 2];
        const bulge = 1.28 + (U.h01(seed, i) - 0.5) * 0.12;
        const c = [x + Math.cos(am) * w / 2 * bulge, y + Math.sin(am) * h / 2 * bulge];
        if (i === 0) g.moveTo(p0[0], p0[1]); g.quadraticCurveTo(c[0], c[1], p1[0], p1[1]);
      }
      g.closePath(); g.fill(); g.stroke();
      if (o.tail) { const [tx, ty] = o.tail; for (let k = 0; k < 3; k++) { const f = 0.45 + k * 0.22, r = (1 - k * 0.3) * Math.min(w, h) * 0.07;
        const px = U.lerp(x, tx, f), py = U.lerp(y + h * 0.3, ty, f); g.beginPath(); g.ellipse(px, py, r * 1.2, r, 0, 0, TAU); g.fill(); g.stroke(); } }
    } else if (kind === 'shout') {
      K.burst(g, x, y, Math.min(w, h) / 2, { spikes: 16, inner: 0.8, sx: w / h,   /* min: sx stretches it to w */ fill, stroke, lw, seed, jag: 0.25 });
    } else {
      g.beginPath(); g.ellipse(x, y, w / 2, h / 2, 0, 0, TAU);
      if (kind === 'whisper') g.setLineDash([lw * 2.5, lw * 2]);
      g.fill(); g.stroke(); g.setLineDash([]);
      if (o.tail) { const [tx, ty] = o.tail; const a = Math.atan2(ty - y, tx - x); const s = 0.22;
        g.beginPath(); g.moveTo(x + Math.cos(a - s) * w * 0.42, y + Math.sin(a - s) * h * 0.42); g.lineTo(tx, ty); g.lineTo(x + Math.cos(a + s) * w * 0.42, y + Math.sin(a + s) * h * 0.42);
        g.fill(); g.stroke(); g.beginPath(); g.ellipse(x, y, w / 2 - lw, h / 2 - lw, 0, 0, TAU); g.fill(); }
    }
    g.restore();
  };
  // a kitchen/utility knife silhouette pointing +x from (x,y) (the handle end)
  K.knife = function (g, x, y, len, rot, o = {}) {
    g.save(); g.translate(x, y); g.rotate(rot || 0); const L = len, hw = L * 0.085;
    g.fillStyle = o.handle || DT.pal.ink; g.beginPath(); g.roundRect(0, -hw * 0.8, L * 0.34, hw * 1.6, hw * 0.5); g.fill();
    g.fillStyle = o.blade || '#e9eef2'; g.beginPath(); g.moveTo(L * 0.34, -hw * 1.05); g.lineTo(L * 0.82, -hw * 0.95); g.quadraticCurveTo(L * 1.0, -hw * 0.5, L, hw * 0.1); g.lineTo(L * 0.34, hw * 0.8); g.closePath(); g.fill();
    if (o.stroke) { g.lineWidth = o.lw || 4; g.strokeStyle = o.stroke; g.stroke(); }
    if (o.blood) { g.fillStyle = DT.pal.red; g.beginPath(); g.moveTo(L * 0.7, -hw * 0.9); g.quadraticCurveTo(L * 0.95, -hw * 0.4, L, hw * 0.1); g.lineTo(L * 0.72, hw * 0.3); g.closePath(); g.fill(); }
    g.restore();
  };
  K.carrot = function (g, x, y, s, rot, o = {}) {
    g.save(); g.translate(x, y); g.rotate(rot || 0);
    g.fillStyle = o.fill || '#ff8a3d'; g.beginPath(); g.moveTo(-s * 0.18, -s * 0.35); g.quadraticCurveTo(0, -s * 0.45, s * 0.18, -s * 0.35); g.lineTo(0, s * 0.55); g.closePath(); g.fill();
    g.fillStyle = o.leaf || '#46b595'; for (const a of [-0.5, 0, 0.5]) { g.save(); g.translate(0, -s * 0.4); g.rotate(a); g.beginPath(); g.ellipse(0, -s * 0.18, s * 0.06, s * 0.2, 0, 0, TAU); g.fill(); g.restore(); }
    g.restore();
  };
  // a lop-eared bunny head icon (pictograms, confetti, stamps)
  K.bunny = function (g, x, y, s, o = {}) {
    g.save(); g.translate(x, y); if (o.rot) g.rotate(o.rot); g.fillStyle = o.fill || DT.pal.ink;
    g.beginPath(); g.arc(0, 0, s * 0.42, 0, TAU); g.fill();
    for (const sd of [-1, 1]) { g.save(); g.translate(sd * s * 0.3, -s * 0.2); g.rotate(sd * (o.perk ? -0.25 : 0.9)); g.beginPath(); g.ellipse(0, s * (o.perk ? -0.45 : 0.4), s * 0.14, s * 0.48, 0, 0, TAU); g.fill(); g.restore(); }
    if (o.eyes) { g.fillStyle = o.eyes; g.beginPath(); g.arc(-s * 0.15, 0, s * 0.07, 0, TAU); g.arc(s * 0.15, 0, s * 0.07, 0, TAU); g.fill(); }
    g.restore();
  };
  // luggage / price tag with a string hole; text lines
  K.tag = function (g, x, y, w, h, lines, o = {}) {
    g.save(); g.translate(x, y); g.rotate(o.rot || 0);
    g.fillStyle = o.fill || '#f6e9c1'; g.strokeStyle = o.stroke || DT.pal.ink; g.lineWidth = o.lw || 5;
    const n = h * 0.35; g.beginPath(); g.moveTo(-w / 2 + n, -h / 2); g.lineTo(w / 2, -h / 2); g.lineTo(w / 2, h / 2); g.lineTo(-w / 2 + n, h / 2); g.lineTo(-w / 2, 0); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = o.hole || DT.pal.paper; g.beginPath(); g.arc(-w / 2 + n * 0.75, 0, h * 0.08, 0, TAU); g.fill(); g.stroke();
    (lines || []).forEach((l, i) => K.text(g, l.text || l, -w / 2 + n * 1.35 + (l.dx || 0), -h / 2 + (i + 1) * h / ((lines.length || 1) + 1) + (l.size || h * 0.2) * 0.35,
      { font: l.font || K.F.mono, size: l.size || h * 0.2, color: l.color || DT.pal.ink, align: 'left' }));
    g.restore();
  };
  // Stamps and seals punch holes (destination-out). Punched straight into the scene canvas those holes became
  // transparent pixels the look pass renders BLACK -- so they are drawn on a private transparent layer and
  // composited: the holes show whatever is beneath, like real ink on paper.
  const _layer = document.createElement('canvas'); _layer.width = W; _layer.height = H;
  function onLayer(g, alpha, fn) {
    const L = _layer.getContext('2d');
    L.setTransform(1, 0, 0, 1, 0, 0); L.globalCompositeOperation = 'source-over'; L.globalAlpha = 1; L.filter = 'none';
    L.clearRect(0, 0, W, H);
    L.setTransform(g.getTransform());
    L.save(); fn(L); L.restore();
    g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha *= alpha; g.drawImage(_layer, 0, 0); g.restore();
  }
  // rubber stamp: bordered text with an inky, broken edge. age drives the slam (null = static)
  K.stamp = function (g, str, x, y, o = {}) {
    const age = o.age; if (age != null && age < 0) return;
    onLayer(g, (o.alpha != null ? o.alpha : 0.92) * (age == null ? 1 : U.clamp(age / 0.05)), (L) => stampRaw(L, str, x, y, o));
  };
  function stampRaw(g, str, x, y, o) {
    const size = o.size || 110, color = o.color || DT.pal.red, age = o.age;
    const k = age == null ? 1 : U.clamp(age / 0.12);
    const s = age == null ? 1 : U.lerp(1.9, 1, U.ease.out3(k));
    g.save(); g.translate(x, y); g.rotate(o.rot != null ? o.rot : -0.12); g.scale(s, s);
    g.font = `${size}px "${o.font || K.F.cond}"`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.letterSpacing = (o.tracking != null ? o.tracking : size * 0.06) + 'px';
    const w = g.measureText(str).width + size * 0.7, h = size * 1.35;
    g.strokeStyle = color; g.lineWidth = size * 0.1; g.strokeRect(-w / 2, -h / 2, w, h);
    if (o.double !== false) { g.lineWidth = size * 0.035; g.strokeRect(-w / 2 + size * 0.14, -h / 2 + size * 0.14, w - size * 0.28, h - size * 0.28); }
    g.fillStyle = color; g.fillText(str, 0, size * 0.04);
    // worn ink: punch holes with the paper colour
    g.globalCompositeOperation = 'destination-out';
    const seed = o.seed || 13;
    for (let i = 0; i < 90; i++) { const px = (U.h01(seed, i, 1) - 0.5) * w, py = (U.h01(seed, i, 2) - 0.5) * h, r = 1 + U.h01(seed, i, 3) * size * 0.05; g.beginPath(); g.arc(px, py, r, 0, TAU); g.fill(); }
    g.restore();
  };
  K.barcode = function (g, x, y, w, h, o = {}) {
    g.save(); g.fillStyle = o.color || DT.pal.ink; let cx = x; const seed = o.seed || 17; let i = 0;
    while (cx < x + w) { const bw = 2 + Math.floor(U.h01(seed, i) * 4) * 2, gap = 2 + Math.floor(U.h01(seed, i, 9) * 3) * 2; if (cx + bw > x + w) break; g.fillRect(cx, y, bw, h); cx += bw + gap; i++; }
    if (o.digits) K.text(g, o.digits, x + w / 2, y + h + (o.digitSize || 22) * 1.1, { font: K.F.mono, size: o.digitSize || 22, color: o.color || DT.pal.ink });
    g.restore();
  };
  // Chinese seal chop: a red square with the character in white (想 = to think AND to want)
  K.seal = function (g, x, y, s, o = {}) {
    const age = o.age; if (age != null && age < 0) return;
    onLayer(g, o.alpha != null ? o.alpha : 1, (L) => sealRaw(L, x, y, s, o));
  };
  function sealRaw(g, x, y, s, o) {
    const ch = o.char || '想', age = o.age;
    const sc = age == null ? 1 : U.lerp(1.8, 1, U.ease.out3(U.clamp(age / 0.12)));
    g.save(); g.translate(x, y); g.rotate(o.rot != null ? o.rot : 0.05); g.scale(sc, sc);
    g.fillStyle = o.color || DT.pal.red; g.beginPath(); g.roundRect(-s / 2, -s / 2, s, s, s * 0.06); g.fill();
    g.globalCompositeOperation = 'destination-out';
    g.font = `${s * 0.82}px "${K.F.cjk}"`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(ch, 0, s * 0.04);
    g.lineWidth = s * 0.035; g.strokeRect(-s / 2 + s * 0.07, -s / 2 + s * 0.07, s - s * 0.14, s - s * 0.14);
    const seed = o.seed || 23; for (let i = 0; i < 40; i++) { g.beginPath(); g.arc((U.h01(seed, i) - 0.5) * s, (U.h01(seed, i, 1) - 0.5) * s, 1 + U.h01(seed, i, 2) * s * 0.02, 0, TAU); g.fill(); }
    g.restore();
  };
  // UI label: filled box + text
  K.label = function (g, str, x, y, o = {}) {
    const size = o.size || 36, pad = o.pad != null ? o.pad : size * 0.35;
    g.save(); g.translate(x, y); g.rotate(o.rot || 0);
    g.font = `${size}px "${o.font || K.F.cond}"`; g.letterSpacing = (o.tracking || 2) + 'px';
    const w = g.measureText(str).width + pad * 2, h = size * 1.25;
    const ax = o.align === 'left' ? 0 : o.align === 'right' ? -w : -w / 2;
    g.fillStyle = o.bg || DT.pal.ink; g.fillRect(ax, -h / 2, w, h);
    if (o.stroke) { g.lineWidth = o.lw || 4; g.strokeStyle = o.stroke; g.strokeRect(ax, -h / 2, w, h); }
    g.fillStyle = o.fg || DT.pal.white; g.textBaseline = 'middle'; g.textAlign = 'left'; g.fillText(str, ax + pad, size * 0.06);
    g.restore();
    return w;
  };
  // leader line from a point on the picture to a label (field guide / loadout). progress draws it on.
  K.callout = function (g, px, py, lx, ly, str, o = {}) {
    const p = o.progress == null ? 1 : U.clamp(o.progress);
    g.save(); g.strokeStyle = o.color || DT.pal.ink; g.lineWidth = o.lw || 3;
    g.beginPath(); g.arc(px, py, (o.dot || 8) * U.clamp(p * 4), 0, TAU); g.fillStyle = o.color || DT.pal.ink; g.fill();
    const k = U.clamp(p * 1.6); g.beginPath(); g.moveTo(px, py); g.lineTo(U.lerp(px, lx, k), U.lerp(py, ly, k)); g.stroke();
    if (p > 0.55) {
      const q = U.clamp((p - 0.55) / 0.45);
      if (o.marker) K.inner(g, str, lx + (o.align === 'right' ? -10 : 10), ly + (o.size || 44) * 0.35, { size: o.size || 44, align: o.align === 'right' ? 'right' : 'left', reveal: q, drawing: o.drawing, seed: o.seed, color: o.textColor || DT.pal.red });
      else K.typeOn(g, str, lx + (o.align === 'right' ? -10 - K.measure(g, str, { size: o.size || 34, font: o.font || K.F.mono }) : 10), ly + (o.size || 34) * 0.35, q, { font: o.font || K.F.mono, size: o.size || 34, color: o.textColor || o.color || DT.pal.ink });
    }
    g.restore();
  };
  // grawlix (#@$%&!): swearing, censored
  K.grawlix = function (g, x, y, size, o = {}) {
    const glyphs = '#@$%&!*?', n = o.n || 6, seed = o.seed || 29, dr = o.drawing || 0;
    let s = ''; for (let i = 0; i < n; i++) s += glyphs[Math.floor(U.h01(seed, i, dr >> 1) * glyphs.length)];
    return K.inner(g, s, x, y, { size, font: K.F.marker2, color: o.color || DT.pal.red, drawing: dr, seed, stroke: o.stroke, strokeW: o.strokeW, align: o.align });
  };

  // ---------------------------------------------------------------- patterns
  K.stripes = function (g, o = {}) {
    const w = o.w || 60, a = o.angle != null ? o.angle : -0.5, cols = o.colors || [DT.pal.pink, DT.pal.hotpink], off = o.offset || 0;
    g.save(); g.translate(W / 2, H / 2); g.rotate(a); const R = 1300;
    for (let x = -R - ((off % (w * cols.length)) + w * cols.length) % (w * cols.length), i = 0; x < R; x += w, i++) { g.fillStyle = cols[((i % cols.length) + cols.length) % cols.length]; g.fillRect(x, -R, w + 0.5, 2 * R); }
    g.restore();
  };
  K.dots = function (g, o = {}) {       // polka dots
    const sp = o.spacing || 90, r = o.r || 18, ox = o.ox || 0, oy = o.oy || 0;
    g.save(); g.fillStyle = o.color || '#ffffff55';
    for (let y = -sp + (oy % sp), row = 0; y < H + sp; y += sp, row++) for (let x = -sp + (ox % sp) + (row % 2 ? sp / 2 : 0); x < W + sp; x += sp) { g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); }
    g.restore();
  };
  K.checker = function (g, o = {}) {
    const s = o.size || 120, cols = o.colors || [DT.pal.ink, DT.pal.white], ox = o.ox || 0, oy = o.oy || 0;
    g.save(); for (let y = -s + (oy % s), j = 0; y < H + s; y += s, j++) for (let x = -s + (ox % s), i = 0; x < W + s; x += s, i++) { g.fillStyle = cols[(i + j) & 1]; g.fillRect(x, y, s + 0.5, s + 0.5); } g.restore();
  };
  // manga focus lines toward (cx, cy)
  K.speedLines = function (g, cx, cy, o = {}) {
    const n = o.n || 90, inner = o.inner || 380, seed = o.seed || 31, dr = o.drawing || 0;
    g.save(); g.fillStyle = o.color || DT.pal.ink; if (o.alpha != null) g.globalAlpha *= o.alpha;
    for (let i = 0; i < n; i++) {
      const a = (i + U.h01(seed, i, dr) * 0.8) * TAU / n, w = (0.004 + U.h01(seed, i, dr, 1) * 0.012) * TAU;
      const r0 = inner * (0.8 + U.h01(seed, i, dr, 2) * 0.7);
      g.beginPath(); g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); g.lineTo(cx + Math.cos(a - w) * 2600, cy + Math.sin(a - w) * 2600); g.lineTo(cx + Math.cos(a + w) * 2600, cy + Math.sin(a + w) * 2600); g.closePath(); g.fill();
    }
    g.restore();
  };
  // a Ben-Day dot field in a rect whose dot radius follows fn(x,y) in 0..1
  K.halftone = function (g, x, y, w, h, o = {}) {
    const sp = o.spacing || 22, fn = o.fn || (() => 0.5);
    g.save(); g.fillStyle = o.color || DT.pal.ink;
    for (let yy = y, row = 0; yy < y + h; yy += sp * 0.866, row++) for (let xx = x + (row % 2 ? sp / 2 : 0); xx < x + w; xx += sp) {
      const r = fn(xx, yy) * sp * 0.55; if (r > 0.4) { g.beginPath(); g.arc(xx, yy, r, 0, TAU); g.fill(); } }
    g.restore();
  };
  K.grid = function (g, o = {}) {
    const s = o.size || 80; g.save(); g.strokeStyle = o.color || '#00000022'; g.lineWidth = o.lw || 2;
    for (let x = (o.ox || 0) % s; x < W; x += s) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
    for (let y = (o.oy || 0) % s; y < H; y += s) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    g.restore();
  };
  // confetti burst launched at time t0 from (x,y): hearts, stars, knives, carrots... physics is closed-form
  K.confetti = function (g, ctx, t0, x, y, o = {}) {
    const age = ctx.t - t0; if (age < 0) return;
    const n = o.n || 60, seed = o.seed || 37, kinds = o.kinds || ['heart', 'star', 'sparkle', 'knife'], cols = o.colors || [DT.pal.red, DT.pal.white, DT.pal.lemon, DT.pal.hotpink, DT.pal.mint];
    const grav = o.gravity != null ? o.gravity : 1400, spd = o.speed || 1500;
    for (let i = 0; i < n; i++) {
      const a = (o.spread != null ? -Math.PI / 2 + (U.h01(seed, i) - 0.5) * o.spread : U.h01(seed, i) * TAU);
      const v = spd * (0.35 + 0.65 * U.h01(seed, i, 1)), drag = 1.8;
      const k = (1 - Math.exp(-drag * age)) / drag;
      const px = x + Math.cos(a) * v * k, py = y + Math.sin(a) * v * k + 0.5 * grav * age * age * 0.6;
      if (py > H + 100) continue;
      const s = (o.size || 34) * (0.6 + 0.8 * U.h01(seed, i, 2)), rot = U.h01(seed, i, 3) * TAU + age * (U.h01(seed, i, 4) - 0.5) * 12;
      const kind = kinds[Math.floor(U.h01(seed, i, 5) * kinds.length)], c = cols[Math.floor(U.h01(seed, i, 6) * cols.length)];
      g.save(); if (o.fade) g.globalAlpha *= U.clamp(1 - (age - o.fade) / 0.6);
      if (kind === 'heart') K.heart(g, px, py, s, { fill: c, rot });
      else if (kind === 'star') K.star(g, px, py, s * 0.5, { fill: c, rot });
      else if (kind === 'sparkle') K.sparkle(g, px, py, s * 0.6, { fill: c, rot });
      else if (kind === 'knife') K.knife(g, px - s * 0.6, py, s * 1.4, rot, {});
      else if (kind === 'carrot') K.carrot(g, px, py, s, rot);
      else if (kind === 'bunny') K.bunny(g, px, py, s, { fill: c, rot });
      else { g.fillStyle = c; g.translate(px, py); g.rotate(rot); g.fillRect(-s * 0.3, -s * 0.12, s * 0.6, s * 0.24); }
      g.restore();
    }
  };

  // ---------------------------------------------------------------- images (cut-outs)
  const A = () => window.DT_ASSETS || {};
  // metadata for a key like 'cut:hero_full/3' -> {w, h, bbox:[x0,y0,x1,y1] of the visible alpha, eyes:[[x,y],[x,y]]|null}
  K.meta = function (key) {
    // a KEYED clip frame is sized/anchored by its figure's box (clips.js DT_CLIPA), not by the whole frame
    if (key.startsWith('clipa:')) { const ci = (window.DT_CLIPA || {})[key.slice(6).split('/')[0]];
      if (ci && ci.bbox) return { w: ci.w, h: ci.h, bbox: ci.bbox, eyes: null }; }
    const k = key.replace(/^[a-z]+:/, '');
    // a gen: key is the FULL picture: never size it by its cut-out's bbox
    const m = A()[k]; if (m) return key.startsWith('gen:') ? { ...m, bbox: [0, 0, m.w, m.h] } : m;
    const img = DT.img(key);
    return img ? { w: img.naturalWidth, h: img.naturalHeight, bbox: [0, 0, img.naturalWidth, img.naturalHeight], eyes: null } : null;
  };
  // K.img(g, key, x, y, {h | w | scale, anchor, rot, flip, alpha, boil: ctx, filter, blend, full, crop})
  //   anchor: 'center' | 'feet' | 'head' | 'left' | 'right' | [ax, ay] (fractions of the BBOX) -- lands at (x, y)
  //   h / w size the BBOX (the visible figure), not the PNG canvas. full: use the whole PNG as the bbox.
  //   boil: pass ctx for a tiny on-twos wobble (keeps stills alive).
  // Returns a transform; K.map(tf, imgX, imgY) -> screen point (source-image pixel coords).
  K.img = function (g, key, x, y, o = {}) {
    const src = o.canvas || DT.img(key); if (!src) return null;
    const pad = o.pad || 0;                                   // derived canvases may carry a border of `pad` px
    const sw = (src.naturalWidth || src.width) - 2 * pad, sh = (src.naturalHeight || src.height) - 2 * pad;
    const m = key ? K.meta(key) : null;
    const [bx0, by0, bx1, by1] = (m && !o.full) ? m.bbox : [0, 0, sw, sh];
    const bw = bx1 - bx0, bh = by1 - by0;
    const s = o.scale || (o.h ? o.h / bh : o.w ? o.w / bw : 1);
    const an = Array.isArray(o.anchor) ? o.anchor : ({ center: [0.5, 0.5], feet: [0.5, 1], head: [0.5, 0], top: [0.5, 0], left: [0, 0.5], right: [1, 0.5] })[o.anchor || 'center'];
    const ax = bx0 + an[0] * bw, ay = by0 + an[1] * bh;
    let rot = o.rot || 0, dx = 0, dy = 0, ds = 1;
    if (o.boil) { const c = o.boil; dx = c.jitter(2.2, 71); dy = c.jitter(2.2, 72); rot += c.jitter(0.004, 73); ds = 1 + c.jitter(0.004, 74); }
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    if (o.filter) g.filter = o.filter;
    if (o.blend) g.globalCompositeOperation = o.blend;
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
    g.translate(x + dx, y + dy); g.rotate(rot); g.scale(s * ds * (o.flip ? -1 : 1), s * ds);
    if (o.crop) { const [cx0, cy0, cx1, cy1] = o.crop; g.drawImage(src, cx0 + pad, cy0 + pad, cx1 - cx0, cy1 - cy0, cx0 - ax, cy0 - ay, cx1 - cx0, cy1 - cy0); }
    else g.drawImage(src, -ax - pad, -ay - pad);
    g.restore();
    return { s: s * ds, ax, ay, x: x + dx, y: y + dy, rot, flip: !!o.flip, key };
  };
  // image pixel -> screen, using the transform K.img returned
  K.map = function (tf, ix, iy) {
    if (!tf) return [0, 0];
    const lx = (ix - tf.ax) * tf.s * (tf.flip ? -1 : 1), ly = (iy - tf.ay) * tf.s;
    const c = Math.cos(tf.rot), s = Math.sin(tf.rot);
    let X = tf.x + lx * c - ly * s, Y = tf.y + lx * s + ly * c;
    if (tf.sq) { const [sx, sy, ox, oy] = tf.sq; X = ox + (X - ox) * sx; Y = oy + (Y - oy) * sy; }   // a squash [sx, sy, ox, oy] a vocab piece may add to the transform
    return [X, Y];
  };
  // the figure's eyes on screen (the manifest's `eyes`, measured by hand; null when unset), for glows / heart pupils / tears
  K.eyes = function (tf) { if (!tf) return null; const m = K.meta(tf.key); if (!m || !m.eyes) return null; return m.eyes.map(([x, y]) => K.map(tf, x, y)); };

  // cached derived sprites (silhouette / sticker / duotone): same pixel grid as the source (+pad)
  const derived = new Map();
  K.silCanvas = function (key, color) {
    const id = 'sil|' + key + '|' + color; let c = derived.get(id); if (c) return c;
    const img = DT.img(key); if (!img) return null;
    c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
    const x = c.getContext('2d'); x.drawImage(img, 0, 0); x.globalCompositeOperation = 'source-in'; x.fillStyle = color; x.fillRect(0, 0, c.width, c.height);
    derived.set(id, c); return c;
  };
  // solid silhouette in one colour (a figure in ink, in white, in red...)
  K.sil = (g, key, x, y, o = {}) => { const c = K.silCanvas(key, o.color || DT.pal.ink); return c ? K.img(g, key, x, y, { ...o, canvas: c }) : null; };
  // die-cut sticker: the figure with a fat white border. THE pop look for cut-outs.
  //   o.border (px in source-image scale, default 14), o.borderColor, o.shadow (colour of a flat offset shadow), o.shadowD
  K.stickerCanvas = function (key, border = 14, color = '#ffffff') {
    const id = 'stk|' + key + '|' + border + '|' + color; let c = derived.get(id); if (c) return c;
    const img = DT.img(key); if (!img) return null;
    const pad = Math.ceil(border) + 2; c = document.createElement('canvas'); c.width = img.naturalWidth + pad * 2; c.height = img.naturalHeight + pad * 2;
    const x = c.getContext('2d');
    const sil = K.silCanvas(key, color);
    const n = 28; for (let i = 0; i < n; i++) { const a = i * TAU / n; x.drawImage(sil, pad + Math.cos(a) * border, pad + Math.sin(a) * border); }
    x.drawImage(sil, pad, pad);
    x.drawImage(img, pad, pad);
    c.pad = pad; derived.set(id, c); return c;
  };
  K.stickerShadowCanvas = function (key, border, color) {
    const id = 'stks|' + key + '|' + border + '|' + color; let c = derived.get(id); if (c) return c;
    const base = K.stickerCanvas(key, border, '#ffffff'); if (!base) return null;
    c = document.createElement('canvas'); c.width = base.width; c.height = base.height; c.pad = base.pad;
    const x = c.getContext('2d'); x.drawImage(base, 0, 0); x.globalCompositeOperation = 'source-in'; x.fillStyle = color; x.fillRect(0, 0, c.width, c.height);
    derived.set(id, c); return c;
  };
  K.sticker = function (g, key, x, y, o = {}) {
    const b = o.border != null ? o.border : 14;
    const c = K.stickerCanvas(key, b, o.borderColor || '#ffffff'); if (!c) return null;
    if (o.shadow) { const d = o.shadowD != null ? o.shadowD : 16; const sc = K.stickerShadowCanvas(key, b, o.shadow);
      K.img(g, key, x + d, y + d, { ...o, canvas: sc, pad: sc.pad }); }
    return K.img(g, key, x, y, { ...o, canvas: c, pad: c.pad });
  };
  // duotone sprite: luminance mapped to [dark, light], alpha kept (Warhol grids)
  K.duoCanvas = function (key, dark, light) {
    const id = 'duo|' + key + '|' + dark + '|' + light; let c = derived.get(id); if (c) return c;
    const img = DT.img(key); if (!img) return null;
    c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
    const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height), p = d.data; const D = U.hexToRgb(dark), Lc = U.hexToRgb(light);
    for (let i = 0; i < p.length; i += 4) { const l = (0.299 * p[i] + 0.587 * p[i + 1] + 0.114 * p[i + 2]) / 255; const t = Math.min(1, Math.max(0, (l - 0.08) / 0.84));
      p[i] = (D[0] + (Lc[0] - D[0]) * t) * 255; p[i + 1] = (D[1] + (Lc[1] - D[1]) * t) * 255; p[i + 2] = (D[2] + (Lc[2] - D[2]) * t) * 255; }
    x.putImageData(d, 0, 0); derived.set(id, c); return c;
  };
  K.duo = (g, key, x, y, dark, light, o = {}) => { const c = K.duoCanvas(key, dark, light); return c ? K.img(g, key, x, y, { ...o, canvas: c }) : null; };

  // ---------------------------------------------------------------- motion
  // camera: centre (x,y) of the world shown at screen centre, zoom, rot
  K.cam = function (g, c = {}) { g.translate(W / 2, H / 2); g.scale(c.zoom || 1, c.zoom || 1); g.rotate(c.rot || 0); g.translate(-(c.x != null ? c.x : W / 2), -(c.y != null ? c.y : H / 2)); };
  K.shake = (ctx, amp, k = 1) => [ctx.jitter(amp, 91 * k), ctx.jitter(amp, 92 * k)];
  // pop-in scale for something that appears at time a (seconds since = age)
  K.pop = (age, d = 0.25) => (age < 0 ? 0 : age >= d ? 1 : U.ease.back(age / d));
  K.wob = (ctx, amp = 0.02, k = 1) => 1 + ctx.jitter(amp, 97 * k);
})();
