// =============================================================================
// shaft.js -- K.s: cards, RP lines, clip handles, hits (anime-OP / SHAFT-style vocabulary). Loaded after kit.js (the
// pop kit K.* is all there too).
//
// The look is SHAFT: black, white and red + each character's colour (DT.pal.who). Colour = who is acting.
// Every function takes the 2D context `g` first (and `ctx` when it animates). Deterministic: time comes from ctx,
// randomness from seeds (U.h01), never Math.random / Date. Times (t0, t1) are seconds or anchors ('B12', 'S3+2b'),
// frame-snapped; a null t0 = the shot's start.
//
//   GROUND   S.ground(g, ctx, {scheme: 'op'|'night'|'dawn'|'black', color, pattern: 'rays'|'grid'|'stripes'|'dots'|'none', fg, alpha})
//   CARDS    S.card(g, text, {bg, fg, font, size, layout, sub, rule, italic, x, y, w, upper, alpha, tracking})
//            S.burst(g, ctx, items, t0, {per, cycle, hold, loop})    flicker cards, `per` frames each
//            S.declare(g, ctx, text, t0, {bg, fg, sub})          the full-screen declaration (a slam + flash)
//            S.chapter(g, ctx, n, title, t0, {sub, bg})          chapter card: a circled numeral + a serif title
//            S.stack(g, ctx, text, t0, {rows, cps, color, size}) a wall of one repeated phrase, typed row by row
//   WORDS    S.say(g, ctx, who, text, t0, {x, y, align, size, cps, hold, tag, maxW})   an RP line, speaker-coloured
//            S.narr(g, ctx, text, t0, {x, y, size, color, cps, hold, align, maxW})     narration (italic serif)
//            S.thought(g, ctx, text, t0, {x, y, size, cps, color, cloud, hold})        a thought (handwriting)
//            S.cloud(g, ctx, cx, cy, rx, ry, {color, fill, lw, seed})                  the scribbly thought cloud
//            S.wrap(g, str, maxW) -> lines (with the current font)
//   CLIPS    S.use(name, {at, from, speed, to, hold, reverse, twos, loop, map}) -> handle
//              handle.key(ctx) (declare it in assets!), handle.frame(ctx), handle.draw(g, ctx, {x,y,w,h, fit, crop,
//              zoom, focus, ax, ay, alpha, filter, flip, rot})
//            S.clipInfo(name) -> {n, w, h} (DT_CLIPS)
//   THE OP   S.nameCard(g, ctx, name, sub, t0, {who, x, y, w, side})  S.credit(g, ctx, role, name, t0, t1, {pos})
//            S.frame(g, x, y, w, h, {color, w1, w2, corner})      Victorian ornament frame
//   THE RP   S.status(g, ctx, {x, y, size, style: 'paper'|'ink', fields, lines, force, alpha})   the status card (ctx.state)
//            S.hud(g, ctx, {alpha, fields, lines})   THE standard corner card (bottom-left): use this, not your own
//            S.STATUS = {stateKey: 'Label', ...}: the fields the card prints   S.statusLines(state, o)   S.HUD (placement)
//   MOTIFS   S.watch(g, ctx, x, y, r, {key, dialAt, time, spin, t0, tick, second, dial, glow, alpha})   a pocket watch
//            S.collage(g, ctx, pieces, {alpha})   cut-paper engravings; S.collageKeys(pieces) (for assets); S.inked
//   HITS     S.circle(g, x, y, r, rot, {color, progress, alpha, lw})   a magic circle
//            S.bolt(g, ctx, x0, y0, x1, y1, t0, t1, {kind: 'fire'|'bolt'|'light', color, r})   a projectile
//            S.ripple(g, ctx, x, y, r, t0, {color})   S.sparks(g, ctx, x, y, t0, {n, color, spread, dir, speed})
//            S.crack(g, ctx, x, y, t0, {n, color, len})    S.hit(ctx, t, {impact, flash, shake, zoom}) -> look patch
//            S.bars(g, ctx, amt, {sides, color})                  letterbox / pillarbox bars
//   TIME     S.snap(t)  S.age(ctx, t0)  S.accents(t0, t1, min)  S.hits(kind, t0, t1, min)  S.flick(ctx, t0, per)
//   KEYS     S.keys = {}: the film's own asset keys for its motifs (films add their own; declare them in assets)
//   FONTS    S.F = {card, didone, fell, dm, type, mono, hand, scrawl, block}  S.fontOf(font, size, italic)
//   COLOUR   S.who(name) -> DT.pal.who[name] (else name itself, a colour); the default accent is DT.pal.accent
// =============================================================================
(function () {
  'use strict';
  const DT = window.DT, U = DT.util, W = DT.W, H = DT.H, P = DT.pal, K = DT.K;
  const TAU = Math.PI * 2, FPS = DT.FPS;
  const S = (K.s = {});

  // ---------------------------------------------------------------- fonts + colours
  // card: Shippori Mincho B1 (weight 800 ONLY: the SHAFT Mincho); didone: Playfair Display SC (small caps labels);
  // fell: IM Fell English (roman + italic: the Victorian book voice); type: Special Elite (the status card)
  S.F = { card: 'Shippori Mincho B1', didone: 'Playfair Display SC', fell: 'IM Fell English', dm: 'DM Serif Display',
    type: 'Special Elite', mono: 'Courier Prime', hand: 'Caveat Brush', scrawl: 'Reenie Beanie', block: 'Anton' };
  const fontOf = (f, size, italic) => `${italic ? 'italic ' : ''}${f === S.F.card ? '800 ' : ''}${size}px "${f}"`;
  S.fontOf = fontOf;
  S.who = (name) => (P.who && P.who[name]) || name || P.white;
  S.keys = {};   // the film's own asset keys ('cut:<job>/<seed>', 'gen:...'), e.g. S.keys.watch for S.watch's case

  // ---------------------------------------------------------------- time helpers
  S.snap = (t) => Math.round(t * FPS) / FPS;
  const T0 = (ctx, t0) => (t0 == null ? ctx.shot.start : typeof t0 === 'number' ? S.snap(t0) : ctx.at(t0));
  S.age = (ctx, t0) => ctx.t - T0(ctx, t0);
  S.accents = (t0, t1, min = 0) => (DT.timing.accents || []).filter((a) => a[0] >= t0 && a[0] < t1 && a[1] >= min).map((a) => a[0]);
  S.hits = (kind, t0, t1, min = 0.3) => (((DT.timing.hits || {})[kind]) || []).filter((a) => a[0] >= t0 && a[0] < t1 && a[1] >= min).map((a) => a[0]);
  // on/off flicker: true on even `per`-frame blocks after t0
  S.flick = (ctx, t0, per = 2) => Math.floor(Math.round((ctx.t - T0(ctx, t0)) * FPS) / per) % 2 === 0;

  // ---------------------------------------------------------------- the ground
  // a flat ground by scheme (o.scheme, else ctx.state.scheme, else 'op'): 'op' = ink, 'night', 'dawn' = paper (its
  // pattern in ink), 'black'; the pattern (red by default) at o.alpha (0.5)
  S.ground = function (g, ctx, o = {}) {
    const sch = o.scheme || (ctx.state && ctx.state.scheme) || 'op';
    const col = o.color || ({ op: P.ink, black: '#000000', night: P.night, dawn: P.paper })[sch] || P.ink;
    g.save();
    g.fillStyle = col; g.fillRect(0, 0, W, H);
    const pat = o.pattern || 'none', fg = o.fg || (sch === 'dawn' ? P.ink : P.red);
    g.globalAlpha *= o.alpha != null ? o.alpha : 0.5;
    if (pat === 'rays') {
      const n = o.n || 24, rot = (o.rot || 0) + (o.spin || 0) * ctx.t;
      g.fillStyle = fg; g.translate(o.x != null ? o.x : W / 2, o.y != null ? o.y : H / 2);
      for (let i = 0; i < n; i++) { const a0 = rot + (i / n) * TAU, a1 = a0 + TAU / n / 2; g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, 2400, a0, a1); g.closePath(); g.fill(); }
    } else if (pat === 'grid') {
      g.strokeStyle = fg; g.lineWidth = o.lw || 2; const s = o.spacing || 120, off = ((o.drift || 0) * ctx.t) % s;
      g.beginPath(); for (let x = -s + off; x < W + s; x += s) { g.moveTo(x, 0); g.lineTo(x, H); } for (let y = -s + off; y < H + s; y += s) { g.moveTo(0, y); g.lineTo(W, y); } g.stroke();
    } else if (pat === 'stripes') {
      g.fillStyle = fg; const s = o.spacing || 90, off = ((o.drift || 0) * ctx.t) % (2 * s);
      g.rotate(o.angle || 0); for (let x = -W - 2 * s + off; x < 2 * W; x += 2 * s) g.fillRect(x, -H, s, 3 * H);
    } else if (pat === 'dots') {
      g.fillStyle = fg; const s = o.spacing || 60, r = o.r || 6;
      for (let y = s / 2; y < H; y += s) for (let x = s / 2 + ((y / s) % 2) * s / 2; x < W; x += s) { g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); }
    }
    g.restore();
  };

  // ---------------------------------------------------------------- cards
  // S.card(g, text, o): the SHAFT title card. text may carry '\n'. bg: null = no fill (text over the picture).
  //   layout: 'center' | 'left' | 'right' | 'vertical' (rotated, up the left edge) | 'stack' (letters stacked)
  //           | 'corner' (small, top-left) | 'low' (bottom third)
  S.card = function (g, text, o = {}) {
    const bg = o.bg === undefined ? P.ink : o.bg, fg = o.fg || (bg === P.paper || bg === P.white || bg === '#fff' || bg === '#ffffff' ? P.ink : P.white);
    const font = o.font || S.F.card, lay = o.layout || 'center';
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    if (bg) { g.fillStyle = bg; g.fillRect(0, 0, W, H); }
    const str = o.upper ? String(text).toUpperCase() : String(text);
    const lines = str.split('\n');
    const maxW = o.w || (lay === 'corner' ? W * 0.4 : W * 0.82);
    let size = o.size || (lay === 'corner' ? 54 : 150);
    g.letterSpacing = (o.tracking != null ? o.tracking : 0) + 'px';
    g.font = fontOf(font, size, o.italic);
    const widest = Math.max(...lines.map((L) => g.measureText(L).width), 1);
    if (!o.noFit && widest > maxW) { size = size * maxW / widest; g.font = fontOf(font, size, o.italic); }
    g.fillStyle = fg; g.textBaseline = 'middle';
    const lh = size * (o.lh || 1.18), bh = lh * lines.length;
    if (lay === 'vertical') {
      g.translate(o.x != null ? o.x : 160, o.y != null ? o.y : H / 2); g.rotate(-Math.PI / 2); g.textAlign = 'center';
      lines.forEach((L, i) => g.fillText(L, 0, (i - (lines.length - 1) / 2) * lh));
    } else if (lay === 'stack') {
      g.textAlign = 'center'; const chars = [...lines[0]], x = o.x != null ? o.x : W / 2, step = size * 0.98;
      const y0 = (o.y != null ? o.y : H / 2) - (chars.length - 1) * step / 2;
      chars.forEach((c, i) => g.fillText(c, x, y0 + i * step));
    } else {
      const align = lay === 'left' || lay === 'corner' ? 'left' : lay === 'right' ? 'right' : 'center';
      g.textAlign = o.align || align;
      const x = o.x != null ? o.x : align === 'left' ? (lay === 'corner' ? 90 : 160) : align === 'right' ? W - 160 : W / 2;
      const y = o.y != null ? o.y : lay === 'corner' ? 110 : lay === 'low' ? H * 0.78 : H / 2;
      const top = y - bh / 2 + lh / 2;
      lines.forEach((L, i) => g.fillText(L, x, top + i * lh));
      if (o.rule) {                    // thin rules above and below the block (the SHAFT title card's lines)
        const rw = Math.min(maxW, widest * size / (o.size || size) + size), rx = align === 'left' ? x : align === 'right' ? x - rw : x - rw / 2;
        g.fillStyle = o.ruleColor || fg; const gap = size * 0.55;
        g.fillRect(rx, top - lh / 2 - gap, rw, Math.max(2, size * 0.03)); g.fillRect(rx, top + bh - lh / 2 + gap * 0.6, rw, Math.max(2, size * 0.03));
      }
      if (o.sub) {
        g.fillStyle = o.subColor || fg; g.font = fontOf(o.subFont || S.F.fell, o.subSize || Math.max(40, size * 0.36), o.subItalic !== false);
        g.letterSpacing = '0px';
        g.fillText(o.sub, x, top + bh - lh / 2 + size * (o.rule ? 1.05 : 0.8));
      }
    }
    g.restore();
  };

  // flicker cards: items = strings or {text, bg, fg, font, layout, size, sub}; each shows `per` frames from t0.
  // Returns the index showing (-1 before/after). o.cycle = the bg colours to rotate through; o.hold keeps the last.
  S.burst = function (g, ctx, items, t0, o = {}) {
    const per = o.per || 3, n = Math.floor(Math.round((ctx.t - T0(ctx, t0)) * FPS) / per);
    if (n < 0) return -1;
    let i = n;
    if (i >= items.length) { if (!o.hold && !o.loop) return -1; i = o.loop ? n % items.length : items.length - 1; }
    const it = typeof items[i] === 'string' ? { text: items[i] } : items[i];
    const cyc = o.cycle || [P.ink, P.red, P.paper];
    const bg = it.bg !== undefined ? it.bg : cyc[i % cyc.length];
    S.card(g, it.text, { size: o.size, font: o.font, layout: o.layout, upper: o.upper, ...it, bg });
    return i;
  };

  // the full-screen declaration: cut in on a 2-frame white flash, the text slams from 1.25x to 1x
  S.declare = function (g, ctx, text, t0, o = {}) {
    const age = S.age(ctx, t0); if (age < 0) return;
    const bg = o.bg === undefined ? P.ink : o.bg;
    if (bg) { g.fillStyle = bg; g.fillRect(0, 0, W, H); }
    const k = U.clamp(age / 0.16), s = U.lerp(1.25, 1, U.ease.out3(k));
    g.save(); g.translate(W / 2, H / 2); g.scale(s, s); g.translate(-W / 2, -H / 2);
    S.card(g, text, { bg: null, fg: o.fg || P.white, size: o.size || 120, sub: o.sub, rule: o.rule !== false, font: o.font, italic: o.italic, subColor: o.subColor, w: o.w });
    g.restore();
    if (age < 2 / FPS - 1e-6) { g.fillStyle = o.flash || '#ffffff'; g.globalAlpha = 1 - age * FPS / 2; g.fillRect(0, 0, W, H); g.globalAlpha = 1; }
  };

  // chapter card: a huge circled numeral + a serif title (the parts of a plan, the acts of a story)
  S.chapter = function (g, ctx, n, title, t0, o = {}) {
    const age = S.age(ctx, t0); if (age < 0) return;
    const bg = o.bg === undefined ? P.red : o.bg, fg = o.fg || P.white;
    if (bg) { g.fillStyle = bg; g.fillRect(0, 0, W, H); }
    const cx = o.x != null ? o.x : W * 0.3, cy = H / 2, r = o.r || 250;
    const k = U.ease.out3(U.clamp(age / 0.25));
    g.save(); g.strokeStyle = fg; g.lineWidth = 14;
    g.beginPath(); g.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + TAU * k); g.stroke();
    g.fillStyle = fg; g.font = fontOf(S.F.card, r * 1.35); g.textAlign = 'center'; g.textBaseline = 'middle';
    g.globalAlpha *= U.clamp(age / 0.08); g.fillText(String(n), cx, cy + r * 0.06);
    g.restore();
    S.card(g, title, { bg: null, fg, layout: 'left', x: cx + r + 90, size: o.size || 110, w: W - (cx + r + 90) - 80, sub: o.sub, rule: true, upper: o.upper !== false });
  };

  // a wall of one repeated phrase, typed row by row (SHAFT's walls of text)
  S.stack = function (g, ctx, text, t0, o = {}) {
    const age = S.age(ctx, t0); if (age < 0) return;
    const rows = o.rows || 9, size = o.size || 84, cps = o.cps || 40, gap = size * 1.12;
    g.save(); g.font = fontOf(o.font || S.F.hand, size, o.italic); g.fillStyle = o.color || P.accent; g.textBaseline = 'middle';
    const unit = text + (o.sep != null ? o.sep : '   '), uw = g.measureText(unit).width;
    let chars = Math.floor(age * cps);
    const y0 = (o.y != null ? o.y : H / 2) - (rows - 1) * gap / 2;
    for (let r = 0; r < rows && chars > 0; r++) {
      const off = ((r * 0.37) % 1) * uw + (o.drift || 0) * age * (r % 2 ? 1 : -1);
      const reps = Math.ceil((W + uw * 2) / uw), line = unit.repeat(reps), n = Math.min(line.length, chars);
      g.fillText(line.slice(0, n), -off, y0 + r * gap);
      chars -= line.length;
    }
    g.restore();
  };

  // ---------------------------------------------------------------- words
  // wrap a string to maxW with the current font
  function wrap(g, str, maxW) {
    const out = [];
    for (const para of String(str).split('\n')) {
      let line = '';
      for (const w of para.split(' ')) { const t = line ? line + ' ' + w : w; if (g.measureText(t).width > maxW && line) { out.push(line); line = w; } else line = t; }
      out.push(line);
    }
    return out;
  }
  S.wrap = wrap;
  // typed text: chars shown by age (cps; 0 = all at once), each line placed; returns the block height
  function typed(g, lines, x, y, lh, age, cps) {
    let n = cps ? Math.floor(age * cps) : 1e9;
    lines.forEach((L, i) => { if (n <= 0) return; g.fillText(L.slice(0, n), x, y + i * lh); n -= L.length + 1; });
  }

  // an RP line (dialogue): white serif, the speaker's colour as a rule + small-caps name tag.
  S.say = function (g, ctx, who, text, t0, o = {}) {
    const age = S.age(ctx, t0); if (age < 0 || (o.hold != null && age > o.hold)) return;
    const size = o.size || 58, col = o.color || S.who(who), maxW = o.maxW || W * 0.62;
    // default y clears the corner status card when it's on (H - 150 collided with S.hud)
    const x = o.x != null ? o.x : W / 2, y = o.y != null ? o.y : (ctx.state && ctx.state.hud ? H - 222 : H - 150), align = o.align || 'center';
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.font = fontOf(o.font || S.F.dm, size, o.italic); g.textAlign = align; g.textBaseline = 'alphabetic';
    const lines = wrap(g, text, maxW), lh = size * 1.18, bw = Math.max(...lines.map((L) => g.measureText(L).width));
    const top = y - (lines.length - 1) * lh;
    const bx = align === 'center' ? x - bw / 2 : align === 'right' ? x - bw : x;
    if (o.box !== false) { g.fillStyle = o.boxColor || 'rgba(6,6,8,0.72)'; g.fillRect(bx - 30, top - size * 1.05, bw + 60, lh * lines.length + size * 0.5); }
    g.fillStyle = col; g.fillRect(bx - 30, top - size * 1.05, 8, lh * lines.length + size * 0.5);
    if (o.tag !== false && who && P.who && P.who[who]) {
      g.font = fontOf(S.F.didone, size * 0.42); g.letterSpacing = size * 0.12 + 'px'; g.textAlign = 'left';
      g.fillText(String(o.tagText || who).toUpperCase(), bx - 18, top - size * 1.05 - size * 0.25);
      g.letterSpacing = '0px'; g.textAlign = align;
    }
    g.font = fontOf(o.font || S.F.dm, size, o.italic); g.fillStyle = o.textColor || P.white;
    typed(g, lines, x, top, lh, age, o.cps != null ? o.cps : 0);
    g.restore();
  };
  // narration: IM Fell italic, centred, white (o.color gives a voice of its own, e.g. P.skyblue; o.glow = a blur px)
  S.narr = function (g, ctx, text, t0, o = {}) {
    const age = S.age(ctx, t0); if (age < 0 || (o.hold != null && age > o.hold)) return;
    const size = o.size || 56, maxW = o.maxW || W * 0.7;
    g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.font = fontOf(o.font || S.F.fell, size, o.italic !== false); g.textAlign = o.align || 'center'; g.textBaseline = 'alphabetic';
    const lines = wrap(g, text, maxW), lh = size * 1.25;
    const y = (o.y != null ? o.y : H / 2) - (lines.length - 1) * lh / 2;
    g.fillStyle = o.color || P.white;
    if (o.glow) { g.shadowColor = o.color || P.white; g.shadowBlur = o.glow; }
    typed(g, lines, o.x != null ? o.x : W / 2, y, lh, age, o.cps != null ? o.cps : 30);
    g.restore();
  };
  // a thought: handwriting in the accent colour, each letter boiling on twos; o.cloud draws the scribbly thought cloud
  S.thought = function (g, ctx, text, t0, o = {}) {
    const age = S.age(ctx, t0); if (age < 0 || (o.hold != null && age > o.hold)) return;
    const size = o.size || 72, col = o.color || P.accent, x = o.x != null ? o.x : W / 2, y = o.y != null ? o.y : H / 2;
    g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.font = fontOf(o.font || S.F.hand, size); g.textBaseline = 'middle'; g.textAlign = 'left';
    const lines = wrap(g, text, o.maxW || W * 0.6), lh = size * 1.15;
    const bw = Math.max(...lines.map((L) => g.measureText(L).width)), bh = lh * lines.length;
    const align = o.align || 'center', x0 = align === 'center' ? x - bw / 2 : align === 'right' ? x - bw : x, y0 = y - bh / 2 + lh / 2;
    if (o.cloud) cloud(g, ctx, x0 + bw / 2, y0 + bh / 2 - lh / 2, bw / 2 + size * 0.9, bh / 2 + size * 0.7, { color: o.cloudColor || col, fill: o.cloudFill, seed: o.seed || 7 });
    g.fillStyle = col;
    let n = o.cps === 0 ? 1e9 : Math.floor(age * (o.cps || 22));
    lines.forEach((L, li) => {
      let cx = x0;
      for (let i = 0; i < L.length; i++) {
        if (n-- <= 0) break;
        const ch = L[i], w = g.measureText(ch).width;
        const j = (U.h01(ctx.drawing, li * 97 + i, 3) - 0.5) * size * 0.05;
        g.save(); g.translate(cx + w / 2, y0 + li * lh + j); g.rotate((U.h01(ctx.drawing, li * 97 + i, 5) - 0.5) * 0.06); g.fillText(ch, -w / 2, 0); g.restore();
        cx += w;
      }
      n -= 1;
    });
    g.restore();
  };
  // the scribbly thought cloud: a bumpy ellipse traced twice by a shaky pen, + two trailing bubbles
  function cloud(g, ctx, cx, cy, rx, ry, o = {}) {
    g.save(); g.strokeStyle = o.color || P.ink; g.lineWidth = o.lw || 5; g.lineJoin = 'round'; g.lineCap = 'round';
    if (o.fill) { g.fillStyle = o.fill; }
    const bumps = o.bumps || 11;
    for (let pass = 0; pass < 2; pass++) {
      g.beginPath();
      for (let i = 0; i <= bumps * 8; i++) {
        const a = (i / (bumps * 8)) * TAU, bump = Math.abs(Math.sin((i / 8) * Math.PI));
        const r = 1 + 0.12 * bump + (U.h01(o.seed || 1, pass, i, ctx.drawing) - 0.5) * 0.02;
        const px = cx + Math.cos(a) * rx * r, py = cy + Math.sin(a) * ry * r;
        i ? g.lineTo(px, py) : g.moveTo(px, py);
      }
      if (o.fill && pass === 0) g.fill();
      g.stroke();
    }
    for (const [dx, dy, rr] of [[-0.55, 1.35, 0.13], [-0.8, 1.75, 0.07]]) { g.beginPath(); g.ellipse(cx + rx * dx, cy + ry * dy, rx * rr, rx * rr * 0.8, 0, 0, TAU); if (o.fill) g.fill(); g.stroke(); }
    g.restore();
  }
  S.cloud = cloud;

  // ---------------------------------------------------------------- clips (image-to-video clips, as upscaled frames)
  // S.use(name, timing) -> a handle. Timing: at = the song time where clip time `from` plays (default: the shot start);
  // speed (1 = real time; 0.5 = slow-mo; -1 = backwards); to/hold = freeze at that clip second; reverse = play from
  // the END backwards; twos = quantise to 12 fps; loop; map(lt, ctx) -> clip seconds (full control: ramps, snaps).
  // ALWAYS declare handle.key(ctx) in the scene's assets(ctx): the frame is loaded before the draw.
  S.clipInfo = (name) => (window.DT_CLIPS || {})[name] || { n: 124, w: 1920, h: 1108 };
  S.use = function (name, o = {}) {
    const info = () => S.clipInfo(name);
    const h = {
      name, o,
      dur() { return info().n / FPS; },
      sec(ctx) {
        const at = o.at != null ? (typeof o.at === 'number' ? S.snap(o.at) : ctx.at(o.at)) : ctx.shot.start;
        const lt = ctx.t - at, D = (info().n - 1) / FPS;
        let s;
        if (o.map) s = o.map(lt, ctx);
        else if (o.reverse) s = (o.from != null ? o.from : D) - lt * (o.speed || 1);
        else s = (o.from || 0) + lt * (o.speed != null ? o.speed : 1);
        if (o.loop) s = ((s % D) + D) % D;
        const stop = o.hold != null ? o.hold : o.to;
        if (stop != null) s = o.reverse || (o.speed || 1) < 0 ? Math.max(s, stop) : Math.min(s, stop);
        if (o.twos) s = Math.floor(s * FPS / 2) * 2 / FPS;
        return U.clamp(s, 0, D);
      },
      frame(ctx) { return Math.round(this.sec(ctx) * FPS); },
      key(ctx) { return `clip:${name}/${this.frame(ctx)}`; },
      // place: {x, y, w, h} (default: the frame), fit 'cover' | 'contain' | 'stretch', crop [x, y, w, h] as clip
      // fractions (the extreme close-up), zoom + focus [fx, fy] (clip fractions), ax/ay (cover alignment 0..1)
      draw(g, ctx, pl = {}) {
        const img = DT.img(this.key(ctx)); if (!img) return null;
        const iw = img.naturalWidth, ih = img.naturalHeight;
        let [cx, cy, cw, ch] = pl.crop || [0, 0, 1, 1];
        const z = pl.zoom || 1;
        if (z !== 1) {
          const f = pl.focus || [cx + cw / 2, cy + ch / 2], nw = cw / z, nh = ch / z;
          cx = U.clamp(f[0] - nw / 2, cx, cx + cw - nw); cy = U.clamp(f[1] - nh / 2, cy, cy + ch - nh); cw = nw; ch = nh;
        }
        let sx = cx * iw, sy = cy * ih, sw = cw * iw, sh = ch * ih;
        const X = pl.x || 0, Y = pl.y || 0, Wd = pl.w || W, Hd = pl.h || H;
        let dx = X, dy = Y, dw = Wd, dh = Hd;
        const fit = pl.fit || 'cover', ra = sw / sh, rb = Wd / Hd;
        if (fit === 'cover') {
          if (ra > rb) { const nw = sh * rb; sx += (sw - nw) * (pl.ax != null ? pl.ax : 0.5); sw = nw; }
          else { const nh = sw / rb; sy += (sh - nh) * (pl.ay != null ? pl.ay : 0.5); sh = nh; }
        } else if (fit === 'contain') {
          if (ra > rb) { dh = Wd / ra; dy += (Hd - dh) / 2; } else { dw = Hd * ra; dx += (Wd - dw) / 2; }
        }
        g.save();
        if (pl.alpha != null) g.globalAlpha *= pl.alpha;
        if (pl.filter) g.filter = pl.filter;
        if (pl.blend) g.globalCompositeOperation = pl.blend;
        g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
        if (pl.rot || pl.flip) { g.translate(dx + dw / 2, dy + dh / 2); if (pl.rot) g.rotate(pl.rot); if (pl.flip) g.scale(-1, 1); g.translate(-(dx + dw / 2), -(dy + dh / 2)); }
        if (pl.clip) { g.beginPath(); pl.clip(g); g.clip(); }
        g.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh);
        g.restore();
        return { x: dx, y: dy, w: dw, h: dh, src: [sx, sy, sw, sh] };
      },
    };
    return h;
  };

  // ---------------------------------------------------------------- the OP furniture
  // Victorian ornament frame: a heavy outer rule, a hairline inside, corner flourishes (quarter circles + diamonds)
  S.frame = function (g, x, y, w, h, o = {}) {
    const col = o.color || P.white, c = o.corner || Math.min(w, h) * 0.08;
    g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.strokeStyle = col; g.fillStyle = col;
    g.lineWidth = o.w1 || 5; g.strokeRect(x, y, w, h);
    const i = (o.w1 || 5) + 9; g.lineWidth = o.w2 || 1.5; g.strokeRect(x + i, y + i, w - 2 * i, h - 2 * i);
    for (const [px, py, sx, sy] of [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]]) {
      g.save(); g.translate(px, py); g.scale(sx, sy);
      g.lineWidth = o.w2 || 1.5; g.beginPath(); g.arc(0, 0, c, 0, Math.PI / 2); g.stroke();
      g.beginPath(); g.arc(0, 0, c * 0.62, 0, Math.PI / 2); g.stroke();
      g.beginPath(); g.moveTo(c * 0.95, c * 0.95); g.lineTo(c * 1.12, c * 0.78); g.lineTo(c * 1.29, c * 0.95); g.lineTo(c * 1.12, c * 1.12); g.closePath(); g.fill();
      g.restore();
    }
    g.restore();
  };

  // OP character card: a black band slides in from the side; the name in Playfair SC, a rule in their colour,
  // the subtitle in Fell italic; the ornament frame around it all
  S.nameCard = function (g, ctx, name, sub, t0, o = {}) {
    const age = S.age(ctx, t0); if (age < 0) return;
    const col = o.color || S.who(o.who), side = o.side || 'left';
    const w = o.w || 880, h = o.h || 250, k = U.ease.out3(U.clamp(age / (o.in || 0.22)));
    const x = o.x != null ? o.x : side === 'left' ? 90 : W - 90 - w, y = o.y != null ? o.y : H - 90 - h;
    const off = (1 - k) * (side === 'left' ? -(x + w + 40) : W - x + 40);
    g.save(); g.translate(off, 0);
    g.fillStyle = o.bg || 'rgba(8,8,10,0.9)'; g.fillRect(x, y, w, h);
    S.frame(g, x + 14, y + 14, w - 28, h - 28, { color: P.white, w1: 3, w2: 1, corner: 26 });
    g.fillStyle = col; g.fillRect(x + 56, y + h * 0.58, w - 112, 5);
    g.fillStyle = P.white; g.textBaseline = 'alphabetic'; g.textAlign = 'left';
    g.font = fontOf(S.F.didone, o.size || 96); g.letterSpacing = (o.size || 96) * 0.06 + 'px';
    let fs = o.size || 96; const nw = g.measureText(name).width; if (nw > w - 112) { fs *= (w - 112) / nw; g.font = fontOf(S.F.didone, fs); g.letterSpacing = fs * 0.06 + 'px'; }
    g.fillText(name, x + 56, y + h * 0.52);
    g.letterSpacing = '0px'; g.font = fontOf(S.F.fell, o.subSize || 44, true); g.fillStyle = o.subColor || '#e7e1d4';
    if (sub) g.fillText(sub, x + 56, y + h * 0.84);
    g.restore();
  };

  // OP staff credit: role in small caps over the name, in a corner; 2-frame fades
  S.credit = function (g, ctx, role, name, t0, t1, o = {}) {
    const a0 = S.age(ctx, t0); if (a0 < 0) return;
    const out = t1 != null ? ctx.t - T0(ctx, t1) : -1; if (out > 2 / FPS) return;
    const a = Math.min(U.clamp(a0 * FPS / 2), out > 0 ? 1 - out * FPS / 2 : 1);
    const pos = o.pos || 'br', m = o.margin || 80;
    const [x, y, align] = Array.isArray(pos) ? [pos[0], pos[1], o.align || 'left'] :
      ({ br: [W - m, H - m, 'right'], bl: [m, H - m, 'left'], tr: [W - m, m + 60, 'right'], tl: [m, m + 60, 'left'] })[pos];
    g.save(); g.globalAlpha *= a; g.textAlign = align; g.textBaseline = 'alphabetic';
    if (o.shadow !== false) { g.shadowColor = 'rgba(0,0,0,0.85)'; g.shadowBlur = 12; }
    g.fillStyle = o.roleColor || '#d9d2c4'; g.font = fontOf(S.F.didone, o.roleSize || 30); g.letterSpacing = '6px';
    g.fillText(role, x, y - (o.size || 58) * 1.05);
    g.letterSpacing = '0px'; g.fillStyle = o.color || P.white; g.font = fontOf(o.font || S.F.dm, o.size || 58, o.italic);
    g.fillText(name, x, y);
    g.restore();
  };

  // ---------------------------------------------------------------- the status card (the RP's own box, typed)
  // The card prints fields of ctx.state (DT.STATE in engine.js), one `Label: value` line each, in S.STATUS's order
  // (state key -> label; arrays print joined with ', '). A film sets its own S.STATUS once in its vocab, or passes
  // o.fields; o.lines(state) -> [lines] replaces the format entirely.
  S.STATUS = { day: 'Day', location: 'Location' };
  S.statusLines = (s, o = {}) => {
    if (o.lines) return o.lines(s);
    const f = o.fields || S.STATUS;
    return Object.keys(f).map((k) => `${f[k]}: ${Array.isArray(s[k]) ? s[k].join(', ') : s[k] != null ? s[k] : ''}`);
  };
  S.status = function (g, ctx, o = {}) {
    const st = o.state ? { ...ctx.state, ...o.state } : ctx.state;
    if (!st || (st.hud === false && !o.force)) return null;
    const size = o.size || 30, style = o.style || 'paper';
    const lines = S.statusLines(st, o), lh = size * 1.3;
    const x = o.x != null ? o.x : 60, y = o.y != null ? o.y : H - 60 - lines.length * lh - size * 0.8;
    g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.font = `${size}px "${S.F.type}"`; g.textBaseline = 'top'; g.textAlign = 'left';
    const w = Math.max(...lines.map((L) => g.measureText(L).width)) + size * 1.6, h = lines.length * lh + size * 1.0;
    g.fillStyle = style === 'paper' ? P.paper : 'rgba(8,8,10,0.88)'; g.fillRect(x, y, w, h);
    g.fillStyle = P.red; g.fillRect(x, y, size * 0.28, h);                        // the red margin rule
    g.fillStyle = style === 'paper' ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
    for (let i = 1; i <= lines.length; i++) g.fillRect(x + size * 0.5, y + size * 0.5 + i * lh - 3, w - size * 0.8, 1.5);
    // what changed at the latest key re-types itself (the old value struck through for a moment)
    let k0 = null; for (const [k] of DT.STATE) { const ks = DT.stateKey(k); if (ks > ctx.t + 1e-6) break; k0 = ks; }
    const age = k0 == null ? 1e9 : ctx.t - k0;
    const before = age < 1.2 && !o.state ? S.statusLines(DT.stateAt(k0 - 1e-3), o) : null;
    lines.forEach((L, i) => {
      const yy = y + size * 0.5 + i * lh, xx = x + size * 0.8;
      g.fillStyle = style === 'paper' ? P.ink : P.white;
      if (before && before[i] !== L) {
        const ci = L.indexOf(':'), head = L.slice(0, ci + 1), old = (before[i] || '').slice(ci + 1), neu = L.slice(ci + 1);
        g.fillText(head, xx, yy); const hx = xx + g.measureText(head).width;
        if (age < 0.25) { g.fillText(old, hx, yy); g.fillStyle = P.red; g.fillRect(hx, yy + size * 0.5, g.measureText(old).width, 3); }
        else { g.fillStyle = P.red; g.fillText(neu.slice(0, Math.floor((age - 0.25) * 34)), hx, yy); }
      } else g.fillText(L, xx, yy);
    });
    g.restore();
    return { x, y, w, h };
  };

  // THE CORNER STATUS CARD (while ctx.state.hud is on): ONE placement for every reel, so it never jumps at a reel
  // boundary. Call S.hud(g, ctx) in over() on story shots; skip it on full-screen cards (declarations, chapter cards,
  // the collage). Stretches without the corner card (an opening, say) can still show the box as an insert:
  // S.status(g, ctx, {force: true, x, y, size, style}).
  S.HUD = { x: 44, bottom: 44, size: 22, style: 'ink', alpha: 0.9 };
  S.hud = function (g, ctx, o = {}) {
    const st = ctx.state; if (!st || st.hud === false) return null;
    const size = S.HUD.size, lh = size * 1.3, h = S.statusLines(st, o).length * lh + size * 1.0;
    return S.status(g, ctx, { fields: o.fields, lines: o.lines, x: S.HUD.x, y: H - S.HUD.bottom - h, size, style: S.HUD.style, alpha: (o.alpha != null ? o.alpha : 1) * S.HUD.alpha });
  };

  // ---------------------------------------------------------------- the pocket watch (a case picture + a code dial)
  // The dial is drawn in code (so the hands obey the song) over an optional case picture (bow, rim): o.key (default
  // S.keys.watch; declare it in the scene's assets) with o.dialAt = [cx, cy, r], the dial's centre and radius in that
  // picture's pixels (default: its centre, half its width). No key: the dial alone. The dial sits at (x, y), radius r.
  // time = hours (11.95 = 11:57); spin = hours per second from t0 (negative = BACK); tick: the minute hand jumps a
  // minute on every beat (time moving FORWARD, one step at a time). o.dial = the dial's colour.
  S.watch = function (g, ctx, x, y, r, o = {}) {
    const key = o.key || S.keys.watch, img = key ? DT.img(key) : null; if (key && !img) return null;
    g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha;
    if (img) {
      const iw = img.naturalWidth, ih = img.naturalHeight, [cx, cy, cr] = o.dialAt || [iw / 2, ih / 2, iw / 2], s = r / cr;
      if (o.glow) { g.shadowColor = o.glowColor || P.white; g.shadowBlur = o.glow; }
      g.drawImage(img, x - cx * s, y - cy * s, iw * s, ih * s);
      g.shadowBlur = 0;
    }
    // the dial
    g.fillStyle = o.dial || '#f6f3ec'; g.beginPath(); g.arc(x, y, r * 0.985, 0, TAU); g.fill();
    g.strokeStyle = P.ink; g.lineWidth = Math.max(1, r * 0.008); g.beginPath(); g.arc(x, y, r * 0.93, 0, TAU); g.stroke();
    for (let i = 0; i < 60; i++) {
      const a = (i / 60) * TAU, c = Math.sin(a), sn = -Math.cos(a), big = i % 5 === 0;
      g.lineWidth = big ? r * 0.018 : r * 0.007;
      g.beginPath(); g.moveTo(x + c * r * (big ? 0.84 : 0.88), y + sn * r * (big ? 0.84 : 0.88)); g.lineTo(x + c * r * 0.93, y + sn * r * 0.93); g.stroke();
    }
    const NUM = ['XII', 'I', 'II', 'III', 'IIII', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
    g.fillStyle = P.ink; g.font = fontOf(S.F.card, r * 0.15); g.textAlign = 'center'; g.textBaseline = 'middle';
    NUM.forEach((n, i) => { const a = (i / 12) * TAU; g.fillText(n, x + Math.sin(a) * r * 0.7, y - Math.cos(a) * r * 0.7); });
    // the hands
    let hrs = o.time != null ? o.time : 10;
    if (o.spin) hrs += o.spin * Math.max(0, S.age(ctx, o.t0));
    if (o.tick) { const beats = Math.floor(ctx.beat - DT.beatAt(T0(ctx, o.t0))); const ph = ctx.beat - Math.floor(ctx.beat); hrs += (Math.max(0, beats) + (beats >= 0 ? U.ease.back(U.clamp(ph / 0.12)) : 0)) / 60; }
    const hA = ((hrs % 12) / 12) * TAU, mA = ((hrs * 60) % 60) / 60 * TAU;
    const hand = (a, len, wd, col) => {
      g.save(); g.translate(x, y); g.rotate(a); g.fillStyle = col;
      g.beginPath(); g.moveTo(-wd, r * 0.1); g.lineTo(-wd * 0.6, -len * 0.75); g.lineTo(-wd * 1.6, -len * 0.8); g.lineTo(0, -len); g.lineTo(wd * 1.6, -len * 0.8); g.lineTo(wd * 0.6, -len * 0.75); g.lineTo(wd, r * 0.1); g.closePath(); g.fill();
      g.restore();
    };
    hand(hA, r * 0.48, r * 0.03, P.ink);
    hand(mA, r * 0.76, r * 0.02, P.ink);
    if (o.second !== false) {
      const sA = o.secAngle != null ? o.secAngle : ((hrs * 3600) % 60) / 60 * TAU;
      g.save(); g.translate(x, y); g.rotate(sA); g.strokeStyle = P.red; g.lineWidth = r * 0.008;
      g.beginPath(); g.moveTo(0, r * 0.16); g.lineTo(0, -r * 0.84); g.stroke(); g.restore();
    }
    g.fillStyle = P.ink; g.beginPath(); g.arc(x, y, r * 0.045, 0, TAU); g.fill();
    g.fillStyle = P.red; g.beginPath(); g.arc(x, y, r * 0.018, 0, TAU); g.fill();
    g.restore();
    return { x, y, r, hours: hrs };
  };

  // ---------------------------------------------------------------- the collage (cut-paper engravings)
  // pieces: [{k: an asset key ('gen:<job>/<seed>', 'cut:...') or '<job>/<seed>' (a whole picture), x, y, w, rot,
  //   crop: [x0,y0,x1,y1] (fractions), shape: 'jag' | 'rect' | 'circle', ink: 'light' (white lines, paper gone) |
  //   'dark' (black lines) | 'paper' (as printed), color (tint for light/dark), t0 (appears: snaps in), t1 (gone),
  //   spin (rad/s), drift [vx, vy] (px/s), jit (px)}]. Engravings (line art on white paper) ink best.
  // Motion is stop-motion: on twos, with a little per-drawing jitter (cut paper, animated a drawing at a time).
  const inkCache = new Map();
  function inked(key, mode, color) {
    const id = key + '|' + mode + '|' + color; let c = inkCache.get(id); if (c) return c;
    const img = DT.img(key); if (!img) return null;
    c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
    const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height), p = d.data;
    const [r, gg, b] = U.hexToRgb(color).map((v) => Math.round(v * 255));
    for (let i = 0; i < p.length; i += 4) {
      const l = (p[i] * 0.299 + p[i + 1] * 0.587 + p[i + 2] * 0.114) / 255;
      const a = U.clamp((1 - l) * 1.35 - 0.05);
      p[i] = r; p[i + 1] = gg; p[i + 2] = b; p[i + 3] = Math.round(a * 255);
    }
    x.putImageData(d, 0, 0); inkCache.set(id, c);
    return c;
  }
  S.inked = inked;
  const pieceKey = (k) => (k.includes(':') ? k : 'gen:' + k);
  S.collageKeys = (pieces) => [...new Set(pieces.map((p) => pieceKey(p.k)))];
  S.collage = function (g, ctx, pieces, o = {}) {
    const tw = ctx.tw;                                   // on twos
    pieces.forEach((p, i) => {
      if (p.t0 != null && ctx.t < T0(ctx, p.t0)) return;
      if (p.t1 != null && ctx.t >= T0(ctx, p.t1)) return;
      const key = pieceKey(p.k), img = DT.img(key); if (!img) return;
      const mode = p.ink || 'light', src = mode === 'paper' ? img : inked(key, mode, p.color || (mode === 'light' ? P.white : P.ink));
      if (!src) return;
      const iw = img.naturalWidth, ih = img.naturalHeight, cr = p.crop || [0, 0, 1, 1];
      const sx = cr[0] * iw, sy = cr[1] * ih, sw = (cr[2] - cr[0]) * iw, sh = (cr[3] - cr[1]) * ih;
      const w = p.w || 600, h = w * sh / sw;
      const lt = tw - (p.t0 != null ? T0(ctx, p.t0) : ctx.shot.start);
      const jit = p.jit != null ? p.jit : 3, seed = (o.seed || 11) * 31 + i;
      const x = p.x + (p.drift ? p.drift[0] * lt : 0) + (U.h01(seed, ctx.drawing, 1) - 0.5) * 2 * jit;
      const y = p.y + (p.drift ? p.drift[1] * lt : 0) + (U.h01(seed, ctx.drawing, 2) - 0.5) * 2 * jit;
      const rot = (p.rot || 0) + (p.spin || 0) * lt + (U.h01(seed, ctx.drawing, 3) - 0.5) * 0.01;
      g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha; if (p.alpha != null) g.globalAlpha *= p.alpha;
      g.translate(x, y); g.rotate(rot); if (p.flip) g.scale(-1, 1);
      // the scissors cut
      const shape = p.shape || 'jag';
      g.beginPath();
      if (shape === 'circle') g.ellipse(0, 0, w / 2, h / 2, 0, 0, TAU);
      else if (shape === 'rect') g.rect(-w / 2, -h / 2, w, h);
      else { const n = 22; for (let k = 0; k < n; k++) { const a = (k / n) * TAU, rr = 0.9 + U.h01(seed, k, 7) * 0.12; const px = Math.cos(a) * w / 2 * rr, py = Math.sin(a) * h / 2 * rr; k ? g.lineTo(px, py) : g.moveTo(px, py); } g.closePath(); }
      if (mode === 'paper') { g.save(); g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 18; g.shadowOffsetX = 8; g.shadowOffsetY = 10; g.fillStyle = '#f4efe2'; g.fill(); g.restore(); }
      g.clip();
      g.drawImage(src, sx, sy, sw, sh, -w / 2, -h / 2, w, h);
      g.restore();
    });
  };

  // ---------------------------------------------------------------- hits
  // a magic circle: two rings, a rune band (ticks + little glyph marks), a star inside. progress 0..1 draws it on.
  S.circle = function (g, x, y, r, rot, o = {}) {
    const col = o.color || P.accent, pr = o.progress != null ? o.progress : 1, lw = o.lw || Math.max(2, r * 0.012);
    g.save(); g.translate(x, y); g.rotate(rot || 0); if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.strokeStyle = col; g.fillStyle = col; g.lineWidth = lw; g.shadowColor = col; g.shadowBlur = o.glow != null ? o.glow : 18;
    const arc = (rr) => { g.beginPath(); g.arc(0, 0, rr, -Math.PI / 2, -Math.PI / 2 + TAU * pr); g.stroke(); };
    arc(r); arc(r * 0.86); arc(r * 0.52);
    const n = 48;
    for (let i = 0; i < n * pr; i++) {
      const a = (i / n) * TAU - Math.PI / 2, c = Math.cos(a), s = Math.sin(a), long = i % 4 === 0;
      g.beginPath(); g.moveTo(c * r * 0.87, s * r * 0.87); g.lineTo(c * r * (long ? 0.99 : 0.95), s * r * (long ? 0.99 : 0.95)); g.stroke();
      if (i % 4 === 2) {   // a little rune: two strokes, seeded
        const h = U.h01(o.seed || 3, i);
        g.save(); g.translate(c * r * 0.93, s * r * 0.93); g.rotate(a + Math.PI / 2);
        g.beginPath(); g.moveTo(-r * 0.02, -r * 0.03); g.lineTo(r * 0.02 * (h > 0.5 ? 1 : -1), r * 0.03); g.moveTo(0, -r * 0.03); g.lineTo(0, r * 0.03); g.stroke(); g.restore();
      }
    }
    // the star (a hexagram), drawn on after the rings
    const sp = U.clamp((pr - 0.4) / 0.6);
    if (sp > 0) {
      for (const off of [0, Math.PI / 3]) {
        g.beginPath();
        for (let k = 0; k <= 3 * sp; k++) { const a = off + (k / 3) * TAU - Math.PI / 2; const px = Math.cos(a) * r * 0.84, py = Math.sin(a) * r * 0.84; k ? g.lineTo(px, py) : g.moveTo(px, py); }
        g.stroke();
      }
    }
    g.restore();
  };
  // a projectile from (x0,y0) to (x1,y1) between t0 and t1: kind 'fire' (an ember ball, a flame trail), 'light' (a
  // glowing orb), 'bolt' (lightning: appears whole at t0, flickers, gone at t1)
  S.bolt = function (g, ctx, x0, y0, x1, y1, t0, t1, o = {}) {
    const a0 = T0(ctx, t0), a1 = T0(ctx, t1); if (ctx.t < a0 || ctx.t > a1 + (o.linger || 0)) return;
    const kind = o.kind || 'fire', col = o.color || (kind === 'fire' ? P.fire : kind === 'bolt' ? P.accent : P.gold);
    const k = U.clamp((ctx.t - a0) / Math.max(0.01, a1 - a0));
    g.save(); g.globalCompositeOperation = 'lighter';
    if (kind === 'bolt') {
      if (ctx.t > a1) { g.restore(); return; }
      for (let pass = 0; pass < 2; pass++) {
        g.strokeStyle = pass ? '#ffffff' : col; g.lineWidth = pass ? 4 : 16; g.shadowColor = col; g.shadowBlur = 30; g.lineJoin = 'miter';
        g.beginPath(); g.moveTo(x0, y0); const n = 11;
        for (let i = 1; i < n; i++) { const f = i / n, nx = -(y1 - y0), ny = x1 - x0, l = Math.hypot(nx, ny) || 1, j = (U.h01(o.seed || 3, ctx.drawing, i) - 0.5) * 90; g.lineTo(x0 + (x1 - x0) * f + nx / l * j, y0 + (y1 - y0) * f + ny / l * j); }
        g.lineTo(x1, y1); g.stroke();
      }
    } else {
      const x = x0 + (x1 - x0) * U.ease.in(k), y = y0 + (y1 - y0) * U.ease.in(k), r = o.r || 60;
      const trail = o.trail || 0.35, n = 14;
      for (let i = n; i >= 0; i--) {
        const f = Math.max(0, U.ease.in(k) - (i / n) * trail * k), tx = x0 + (x1 - x0) * f, ty = y0 + (y1 - y0) * f, rr = r * (1 - i / (n + 2)) * (0.8 + 0.4 * U.h01(ctx.drawing, i));
        g.fillStyle = i < 3 ? '#fff4d8' : col; g.globalAlpha = (1 - i / (n + 1)) * 0.55;
        g.beginPath(); g.arc(tx, ty, rr, 0, TAU); g.fill();
      }
      g.globalAlpha = 1; g.fillStyle = '#ffffff'; g.shadowColor = col; g.shadowBlur = 50; g.beginPath(); g.arc(x, y, r * 0.45, 0, TAU); g.fill();
    }
    g.restore();
  };
  // rings expanding from an impact point (a shield taking a hit)
  S.ripple = function (g, ctx, x, y, r, t0, o = {}) {
    const a = S.age(ctx, t0); if (a < 0 || a > (o.dur || 0.6)) return;
    g.save(); g.strokeStyle = o.color || P.accent; g.shadowColor = o.color || P.accent; g.shadowBlur = 20;
    for (let i = 0; i < (o.n || 3); i++) { const k = U.clamp((a - i * 0.07) / (o.dur || 0.6)); if (k <= 0) continue; g.globalAlpha = (1 - k) * 0.9; g.lineWidth = 10 * (1 - k) + 2; g.beginPath(); g.ellipse(x, y, r * k, r * k * (o.squash || 0.75), 0, 0, TAU); g.stroke(); }
    g.restore();
  };
  // a spark burst: n streaks flying out of (x, y) in a cone (dir, spread), falling, fading
  S.sparks = function (g, ctx, x, y, t0, o = {}) {
    const a = S.age(ctx, t0), life = o.life || 0.55; if (a < 0 || a > life) return;
    const n = o.n || 36, dir = o.dir != null ? o.dir : -Math.PI / 2, spread = o.spread != null ? o.spread : Math.PI, sp = o.speed || 1400;
    g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const ang = dir + (U.h01(o.seed || 5, i, 1) - 0.5) * spread, v = sp * (0.35 + 0.65 * U.h01(o.seed || 5, i, 2)), tt = a * (0.7 + 0.3 * U.h01(o.seed || 5, i, 3));
      const px = x + Math.cos(ang) * v * tt, py = y + Math.sin(ang) * v * tt + 900 * tt * tt;
      const vx = Math.cos(ang) * v, vy = Math.sin(ang) * v + 1800 * tt, l = 0.03;
      g.strokeStyle = i % 3 ? (o.color || P.fire) : '#fff6d8'; g.globalAlpha = 1 - a / life; g.lineWidth = o.w || 4;
      g.beginPath(); g.moveTo(px, py); g.lineTo(px - vx * l, py - vy * l); g.stroke();
    }
    g.restore();
  };
  // glass cracks radiating from (x, y): drawn whole at t0 (a snap, never grown)
  S.crack = function (g, ctx, x, y, t0, o = {}) {
    const a = S.age(ctx, t0); if (a < 0 || (o.hold != null && a > o.hold)) return;
    const n = o.n || 9, len = o.len || 1400, seed = o.seed || 17;
    g.save(); g.strokeStyle = o.color || '#ffffff'; g.lineJoin = 'miter'; g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 4;
    for (let i = 0; i < n; i++) {
      let ang = (i / n) * TAU + (U.h01(seed, i) - 0.5) * 0.5, px = x, py = y, L = len * (0.5 + 0.5 * U.h01(seed, i, 2));
      g.lineWidth = o.w || 3; g.beginPath(); g.moveTo(px, py);
      for (let s = 0; s < 9; s++) { ang += (U.h01(seed, i, s, 3) - 0.5) * 0.5; const d = L / 9; px += Math.cos(ang) * d; py += Math.sin(ang) * d; g.lineTo(px, py);
        if (U.h01(seed, i, s, 4) > 0.72) { const b = ang + (U.h01(seed, i, s, 5) > 0.5 ? 0.9 : -0.9); g.moveTo(px, py); g.lineTo(px + Math.cos(b) * d * 1.4, py + Math.sin(b) * d * 1.4); g.moveTo(px, py); } }
      g.stroke();
    }
    for (let k = 1; k <= 2; k++) { g.lineWidth = 1.5; g.beginPath(); for (let i = 0; i <= n; i++) { const ang = (i / n) * TAU, rr = 60 * k + U.h01(seed, i, k, 9) * 40 * k; const px = x + Math.cos(ang) * rr, py = y + Math.sin(ang) * rr; i ? g.lineTo(px, py) : g.moveTo(px, py); } g.stroke(); }
    g.restore();
  };
  // a look patch for an impact at t: a 1-frame impact (white/black/red), a flash, a shake, a punch-in
  S.hit = function (ctx, t, o = {}) {
    const x = ctx.t - (typeof t === 'number' ? S.snap(t) : ctx.at(t)); if (x < 0 || x > 0.6) return {};
    const out = {};
    const nf = (o.frames || 1) / FPS;
    if (x < nf - 1e-6) { if (o.impact !== false && o.impact !== 0) out.impact = o.impact || 1; if (o.invert) out.invert = 1; }   // impact 0 = none   // float guard: a frame later x can be a hair under 1/FPS
    // the impact frame stays crisp black/white/red: its flash starts on the frame after it
    const x0 = o.impact !== false && o.impact !== 0 ? nf : 0, f = x < x0 - 1e-6 ? 0 : Math.exp(-(x - x0) / (o.decay || 0.09));
    out.flash = (o.flash != null ? o.flash : 0.5) * f; out.flashColor = o.flashColor || '#ffffff';
    const amp = (o.shake != null ? o.shake : 22) * f; out.shake = [ctx.jitter(amp, 81), ctx.jitter(amp, 82)];
    out.zoom = 1 + (o.zoom != null ? o.zoom : 0.05) * f;
    return out;
  };
  // letterbox (top+bottom) or pillarbox (o.sides) bars: amt 0..1 of max (default 0.36 of the half-frame)
  S.bars = function (g, ctx, amt, o = {}) {
    const k = U.clamp(amt) * (o.max || 0.36);
    g.save(); g.fillStyle = o.color || '#000';
    if (o.sides) { const w = W / 2 * k; g.fillRect(0, 0, w, H); g.fillRect(W - w, 0, w, H); }
    else { const h = H / 2 * k; g.fillRect(0, 0, W, h); g.fillRect(0, H - h, W, h); }
    g.restore();
  };
})();
