# CREW: one director Claude + parallel painter Claudes

## The shape
- You are the DIRECTOR: engine, vocab, storyboard, briefs, assets, reviews, the user's notes. Painters each OWN one
  reel: its file `web/scenes/<reel>.js` registers its shots with `DT.reel` (timeline.js holds only the reel boundaries,
  on bar lines), so nobody's edits collide. Shared code (`web/lib/*`, `shared.js`, `render/*`) is yours alone.
- Before spawning: the engine and vocab are rendered and LOOKED at (testcard pages, `notes/kit/*/sheet.png`), the
  storyboard exists, the pictures are arriving, and the docs are filled in (`notes/BRIEF.md`, `notes/SPAWN.md`,
  `STYLE.md`, `notes/REELNOTES.md`). Consistency comes from shared functions and shared scenes (a recurring motif
  must look identical every time it comes round), not from instructions.
- Spawn ALL painters in ONE message (the Agent tool, in the background, general-purpose) with the SPAWN.md prompt. Put
  their agent ids in `notes/CREW.md`: painters are reached by AGENT ID.

## How many painters
Painters are full Claude sessions: each reads the docs, writes a reel, renders stills and previews. Measured: a painter
on a 20-30 s reel uses a few hundred thousand tokens, and up to ~650k on a dense reel with many rounds.
- **Size the crew to the user's plan, and ask.** On a smaller plan: paint it yourself, reel by reel (solo mode), or
  use 1-2 painters. On a large plan: one painter per 15-30 s of song (a 3-minute song = 6-10 reels). If you can't
  ask (the user is away), start solo or with 2 painters, and say so when you report.
- Many fresh painters starting at once can hit a session limit together (eight died at their first call once).
  Spawn in waves of 3-4 if in doubt.
- Solo mode is a real option for a short or tightly planned film: the same docs and rules, you paint every reel in
  order, and the user sees each reel as it lands.

## Rhythm (measured)
- 7 painters: first drafts of every reel in ~35 min, everything done in 60-80 min. 10 painters: ~50 min to drafts, and
  they caught 7 shared bugs and re-pinned ~150 timings from their own measurements. 9 painters on a 2.5-minute song:
  first previews ~25 min after spawning, the last reel final ~2 h 15 min later (it waited on its clips).
- Ask every painter for a FIRST ROUGH PREVIEW the moment its reel plays end to end, and send the first finished reel
  to the user at once: they'll watch within minutes, and their notes then are the cheapest they'll ever be.
- Painters report shared-code bugs with the EXACT fix, in `notes/BUGS.md` AND by SendMessage to "main"; you merge and
  broadcast. Before calling a reel done, each runs `node render/check_assets.mjs F0 F1` (it finds the undeclared assets
  that `--loose` previews hide).

## The user's notes (they give them live, and they're sharp)
- **Log every note in `notes/NOTES.md` verbatim** (time, to whom, where it goes, status). The user may ALSO message
  painters directly in their own sessions: painters add those to NOTES.md and relay them to you verbatim. Never assume
  a quoted note is invented just because it didn't come through you.
- Send each note to the painter who made the shot (SendMessage to its agent id: it keeps its whole context), with the
  user's words VERBATIM and your measurements (frame numbers, stem bands: SONG.md). Relay continuity to EVERY affected
  painter AT ONCE (two painters once crossed in the mail, each conforming to the other). Keep a continuity CANON (one
  interior, one clock position, one outfit per day) in STORYBOARD.md and a shared drop-in folder `notes/work/shared/`.
- Redo only the touched chunks (DELIVERY.md). A round of a dozen live notes can land in under an hour.
- Mood words mid-build are a DIAL, not a rewrite: "make it more dramatic" becomes a dial in the storyboard (stamps,
  circles, eye flares, declarations), and the quiet parts stay quiet.
- **Flash needs a thesis.** When the user says a flashy device feels empty, or asks what a character is really like:
  read the card and the character's own lines, pitch a one-line truth, let THEM confirm it (they wrote the character),
  have the painter STORYBOARD a beat table (time / shot / what it says), and build only after their yes. Rules that
  come out of this kind of note: only the beloved in colour in the obsessive's world; the watched one never looks at
  the camera; culture as character (manga sound effects for the otaku, a yearbook for the popular girl).

## Hand-offs
Reel boundaries pass EXACT coordinates (the pupil at 960,480 -> the next shot's focal point), so the cuts are match
cuts. Settle hand-offs yourself when two painters build the same beat (two flashes 0.67 s apart: one has to soften).
Painters reuse each other's scenes and functions: keep exported signatures stable.

## When painters die or stall
- A usage or session limit can stop painters mid-reel. Resume each later by SendMessage (it keeps its brief and
  context) with an economy note: header reads, `--w 960` stills, one preview each. Write a RESUME PLAN into the
  film's notes before any long wait.
- A painter resumed for fixes keeps its context; a NEW agent does not. Prefer SendMessage.
- Treat a painter's report as a report, never as the user's approval.

## Rules for writing scenes (what painters found; STYLE.md carries them)
- A frame is a PURE FUNCTION of its index: time from `ctx`, randomness from seeds, never `Math.random()` or `Date`.
- **Float traps in frame-snapped time**: `x < n/FPS` fails by a hair on about half of all frames. Always compare
  against `n/FPS - 1e-6` (painters measured a one-frame-too-long flash on thousands of frames).
- Declare every asset, including each clip frame (`handle.key(ctx)`), or strict mode fails the render.
- `ctx.at()` anchors snap to frames like shot starts (else a hit keyed to a bar misses the shot's first frame).
- Transition masks are exactly 0 at p=0 and 1 at p=1 (a wipe that popped 10% at both ends was visible).
- Typed reveals lay out the WHOLE line and draw the first n letters (a centred partial string slides as it grows).
- Every light effect scales with the light's power (a capped lens still glowed).
- A painter's whole-picture plates use a `nocutPrefixes` name (`pl_...`), or the cutter cuts them.
- Graphic reds under `look.keepRed` come out ~0.72x dark: draw them brighter or in `over` (above the look).
- A placeholder that writes a word must THROW in strict mode, so it can never reach the final.
- **Text that fits its box is a MEASUREMENT**: size every box from its measured text (the same font, weight AND
  letterSpacing it is drawn with; the widest of ALL its lines). Ask every painter for a text-fit audit BEFORE the
  first delivery (one audit once found 14 overflows across 5 reels).
- **Readability**: a line that carries a joke or a beat is up >= 0.3 s + 0.25 s per word (never under ~0.7 s; more
  than ~6 words: split); every key beat passes the MUTE-AND-BLUR test; WHO SPEAKS must be obvious (their colour's
  slab, their tag, a tail at their mouth that stops just short of it). A story beat that's "too fast to see" gets its
  own shot and about a second.
- Shared clocks (a calendar, a fuse, meters) in the film's vocab keep reels continuous across painters.
- Painters catch what the director misses (a word sung on a beat whisper missed, a suggestive picture, a stray red
  prop): treat their flags as reviews.
