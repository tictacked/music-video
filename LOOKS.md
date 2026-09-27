# LOOKS: choosing a direction

## Keep changing the look
Variety is the feature. The films people love most are loved *because* each found its own look in its own source.
Find THIS song's and THIS character's rule and let the look follow; the kit is machinery, not a house style. Don't
reuse the last film's look because it's there.

## What a look is made of
1. **THE RULE** (SOURCE.md): one visual rule from the source's own metaphor. It decides more than anything else.
2. **A palette with owners**: whose colour is whose; one reserved colour that belongs to one character or one idea.
3. **Type**: one display face, one text face, maybe a hand. The kit carries 30 families (below).
4. **A pace** (SONG.md): how fast each section cuts, what stutters, what holds.
5. **A texture**: film grain, halftone, paper, CRT, ink, clean digital.
6. **A medium or a borrowed form** (optional): a game UI, a chat window, a TV broadcast, silent-film cards, a manga page.
Mock up one frame per key moment before committing, and show the user two directions side by side if they're unsure.

## The engine's pieces (web/lib/engine.js; its header lists every key)
Each shot draws in two Canvas2D layers (`draw` = the world, `over` = above the look: type, HUD, credits), then a
WebGL LOOK pass, then a TRANSITION into the next shot, then a POST pass for the whole frame.
- **Looks** (a shot's `look(ctx)` returns any of these; all default to off):
  - colour: `cold`/`warm` tints, `duotone`, `halftone`, `posterize`, `sat`, `bright`, `grade` + `gradeAmt`, `hue`,
    `mono` (1-bit, with its own dark and light), `invert`;
  - keep one colour: `keepRed` (everything to two inks except TRUE red: an ink-and-paper world with one colour
    kept), `gmap` (a 4-stop gradient map on luminance: a limited palette per reel, true red surviving by
    `gmapKeepRed`), `invertKeepRed`;
  - film and video: `grain`, `halation`, `leak` (light leaks), `vhs`, `scan` (CRT lines), `glitch`, `ca`
    (chromatic aberration), `reg` (colour plates out of register), `seam` (the picture pushed apart along a line);
  - surface: `linen`, `paper` (an embossed texture);
  - optics: `blur`, `radial`, `vignette`, `ripple`, `swirl`;
  - hits: `impact` (a black-and-white impact frame), `flash`, `shake`, `zoom`, `rot`.
- **Transitions** (a shot's `trans: {type, dur, at, par, color}`): cut, dissolve, dip, flash, ink, blush, heart,
  slash, wipe, tear, blink, zoom, glitch, circle, blinds, mosaic, split, checker, wave, tide, ripple, spin, leak, film,
  page, star, whip, irisdip, merge, reg, static, slices, negflash, seam, patch, clock, shutter, jigsaw, shatter. See one
  alone at `web/index.html?trtest=<type>`.
- **The pop kit** (`web/lib/kit.js`, K.*): kinetic type (`K.slam`, `K.typeOn`, `K.inner` an inner voice in scrawl),
  markers and scribbles (rough.js), shapes (hearts, stars, bursts, rays, speech bubbles, stamps, seals, barcodes),
  patterns (stripes, dots, speed lines, confetti), die-cut stickers, silhouettes, a camera (`K.cam`), shake, pop, boil.
- **Cards, RP lines, clips, hits** (`web/lib/shaft.js`, K.s.*): full-screen text cards in the anime-OP style
  (declarations, chapter cards, flicker bursts, walls of one phrase), RP lines coloured by speaker (`S.say`,
  narration, thoughts), OP credits and name cards, a status card / HUD drawn from `ctx.state`, magic circles, bolts,
  ripples, sparks, cracks, letterbox bars, and `K.s.use` for clips.
- **Fonts** (setup.py downloads them): Dela Gothic One, Anton, Caveat Brush, Permanent Marker, Reenie Beanie, Space
  Mono, DM Serif Display, Mochiy Pop One, Ma Shan Zheng (Chinese brush), Rubik Mono One, Bungee, Shrikhand, Pacifico,
  Caprasimo, Monoton, Rock Salt, Special Elite, Fontdiner Swanky, Yellowtail, Righteous, Limelight, Knewave,
  DotGothic16 (pixel, Japanese), VT323, Rampart One, Courier Prime, IM Fell English, Playfair Display SC, Graduate,
  Shippori Mincho B1 (the heavy Japanese Mincho of anime title cards). Another Google font: add it to setup.py's list
  and index.html.
- **The film's own vocabulary** goes in `web/lib/vocab.js` (K.v): every film needs pieces nobody has drawn before,
  whatever its RULE asks for (a card game's cards, a train timetable, a chat window). Write them, give each a testcard
  page, look at it, then hand it to painters. A piece worth keeping for later films goes into `<skill>/kit/vocab/`.

## Directions nobody has tried yet with this kit (starting points, not rules)
- a visual-novel UI: textbox, sprites, choices (an RP is already a VN script);
- a pixel / retro-PC game shell;
- a JRPG battle screen fed by the RP's own status boxes;
- manga pages with panel reads and page turns;
- stained glass (light through colour);
- papercut shadow theatre;
- a 16mm home movie;
- an illuminated manuscript;
- the chat log itself as the set: a chat window the story breaks out of.

## Real motion vs stills
An images-only film leans on the engine: camera moves across big plates, cut-outs in layers (parallax), boil on
twos, squash and stretch, slams, cards, transitions on the beat. Clips (CLIPS.md) add bodies moving: dancing,
fighting, hair in wind. Mixed is common: clips for the hero moments, stills for everything else.

## If you build a watercolour engine instead (p5.js + p5.brush)
The kit's engine is Canvas2D + WebGL; a hand-painted watercolour film needs a different one. It works with p5.js 2.x
+ p5.brush 2.x: paint the world in TRUE DAYLIGHT watercolour, and let a light map (R/G/B = light slots) and a relight
shader make night (one slot as a one-colour ramp: lamplight, moonlight; another as true colour). Glows are additive,
in an overlay. The traps, each of which cost an hour:
- Fills are PIGMENT (spectral mixing): yellow over blue = green mud. **Light is never paint.**
- Watercolour fills are translucent: pale over paper, pale even when dark over a bright area. Use an opaque wash base
  under anything that needs real value, and solid silhouettes where a figure must read.
- In a one-colour light pool the lead vanishes (honey on honey): draw them in the overlay, after the glows, as a
  silhouette.
- Strokes silently vanish when raw coordinates leave about +-1920 x +-1080 (a stroke that STARTS off-canvas never
  draws). Polygon fills are unaffected.
- Each wash polygon costs ~8 ms: use strokes for many small details.
- Few-vertex big fills grow sawtooth edges: subdivide the polygon first.
- An active fill leaks into later washes: clear the fill first.
- Strokes batch per colour until the frame ends: flush before switching framebuffers.
- p5 2.x `redraw()` is async (await it); `scale()` scales the brush tip too.
- Single-stroke (Hershey) fonts: some glyphs read as others ('o' as 'a' in one script face); CJK needs hand-written
  strokes.
