// =============================================================================
// testcard.js -- the DIRECTOR's kit demo: the engine's pieces on one page each. Not in the film (the placeholder reel
// shows it until the storyboard exists). Add a page per piece of the film's own vocabulary (web/lib/vocab.js) as you
// write it, and look at it before any painter uses it.
//   node render/stills.mjs --scene testcard --params '{"page":"type"}' --dur 3 --n 4 --sheet --out notes/kit/type
//   node render/stills.mjs --scene testcard --params '{"page":"looks","look":{"keepRed":1}}' --n 1 --out notes/kit/ink
// pages: type (every font), shapes (kit patterns + shapes), looks (a colour chart under params.look: try keepRed,
//        gmap + gmapStops, duo, halftone, invert, posterize, mono, cold...)
// transitions alone: web/index.html?trtest=shatter (trA -> trB at 2.0 s)
// =============================================================================
(function () {
  const { K, util: U } = DT, W = DT.W, H = DT.H;
  const FONTS = ['Dela Gothic One', 'Anton', 'Caveat Brush', 'Permanent Marker', 'Reenie Beanie', 'Space Mono', 'DM Serif Display',
    'Mochiy Pop One', 'Rubik Mono One', 'Bungee', 'Shrikhand', 'Pacifico', 'Caprasimo', 'Monoton', 'Rock Salt', 'Special Elite',
    'Fontdiner Swanky', 'Yellowtail', 'Righteous', 'Limelight', 'Knewave', 'DotGothic16', 'VT323', 'Rampart One', 'Courier Prime',
    'IM Fell English', 'Playfair Display SC', 'Graduate', 'Shippori Mincho B1'];
  DT.scene('testcard', {
    bg: '#f6f1e7',
    look(ctx) { return ctx.params.look || {}; },
    draw(g, ctx) {
      const pg = ctx.params.page || 'type', t0 = ctx.shot.start;
      if (pg === 'type') {
        g.fillStyle = '#f6f1e7'; g.fillRect(0, 0, W, H);
        FONTS.forEach((f, i) => {
          const col = i % 3, row = Math.floor(i / 3);
          K.text(g, f, 60 + col * 620, 90 + row * 98, { font: f, size: 44, align: 'left', color: '#1b1a1f',
            weight: f === 'Shippori Mincho B1' ? 800 : '' });
        });
      } else if (pg === 'shapes') {
        K.stripes(g, { colors: ['#1b1a1f', '#2a2830'], w: 90, offset: (ctx.t - t0) * 120 });
        K.dots(g, { color: '#ffffff22', spacing: 80, r: 10 });
        K.burst(g, 420, 380, 260, { fill: '#ffd400', stroke: '#1b1a1f', seed: 3, drawing: ctx.drawing });
        K.star(g, 1000, 380, 220, { fill: '#ff5aa0', stroke: '#1b1a1f', rot: (ctx.t - t0) * 0.5 });
        K.heart(g, 1500, 400, 200, { fill: '#d11f2f' });
        K.text(g, 'K.burst  K.star  K.heart  K.stripes  K.dots', 960, 900, { size: 56, color: '#f6f1e7', font: 'Anton' });
      } else if (pg === 'looks') {
        // a colour chart: a hue sweep, a grey ramp, TRUE red next to the reds that must not count as red
        for (let i = 0; i < 24; i++) { g.fillStyle = `hsl(${i * 15}, 85%, 55%)`; g.fillRect(i * 80, 0, 80, 360); }
        for (let i = 0; i < 16; i++) { const v = Math.round(i * 17); g.fillStyle = `rgb(${v},${v},${v})`; g.fillRect(i * 120, 360, 120, 240); }
        const sw = [['true red', '#d11f2f'], ['blood', '#8a0f18'], ['brown hair', '#6b3a22'], ['auburn', '#8c3b2a'],
          ['skin', '#f1c7a8'], ['blush', '#ef9a9a'], ['amber', '#e8a13a'], ['orange', '#f26b1d']];
        sw.forEach(([name, c], i) => {
          g.fillStyle = c; g.fillRect(i * 240, 600, 240, 360);
          K.text(g, name, i * 240 + 120, 1010, { size: 30, color: '#1b1a1f', font: 'Space Mono' });
        });
        K.text(g, 'look: ' + JSON.stringify(ctx.params.look || {}), 960, 1062, { size: 26, color: '#1b1a1f', font: 'Space Mono' });
      }
    },
  });
  DT.scene('trA', { bg: '#f6f1e7', draw(g) { g.fillStyle = '#f6f1e7'; g.fillRect(0, 0, W, H); K.text(g, 'A', W / 2, H / 2 + 150, { size: 420, color: '#1b1a1f' }); } });
  DT.scene('trB', { bg: '#d11f2f', draw(g) { K.stripes(g, { colors: ['#d11f2f', '#1b1a1f'], w: 140 }); K.text(g, 'B', W / 2, H / 2 + 150, { size: 420, color: '#f6f1e7' }); } });
})();
