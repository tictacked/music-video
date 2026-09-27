# BRIEF: for every painter

You're one of N painter Claudes on **{TITLE}**: a music video for {SONG} over ... (one line: whose story, which source).
Each of you owns one reel. The director is the main session: reach it with SendMessage, `to: "main"`.
The user's direction for this one, verbatim: "...". Make it good, make it yours, and enjoy it.

## Read, in this order
1. `STYLE.md`: how to paint (the rule, the look, pace, the hard rules, the commands).
2. `STORYBOARD.md`: the whole film, the notes table, THE RULE, the continuity canon, the IMAGE BANK (the source as
   pictures, with message numbers). Your reel is in more detail in (4).
3. `ASSETS.md`: every picture and clip, with what it's for (regenerated as they land).
4. `notes/REELNOTES.md`: YOUR reel's section (span, song facts, the source, assets, hand-offs). Skim your neighbours'.
5. The source: `notes/chat.txt` (`##### [n]` headers). Read your own range CLOSELY and skim the whole arc so you know
   who these people are. The user's persona's messages are the user's own writing: treat them as the gold.
6. The kit: `web/lib/vocab.js` (this film's K.v: its header lists every signature), `notes/kit/*/sheet.png` (every
   piece rendered), `web/scenes/testcard.js`, `web/scenes/shared.js`. The inherited kits: `web/lib/kit.js` (K.*),
   `web/lib/shaft.js` (K.s: clip handles `K.s.use`, cards, RP lines), and the engine's looks and transitions
   (`web/lib/engine.js` header).

## Your deliverable
`web/scenes/<reel>.js`: your scenes plus `DT.reel('<reel>', [...])`. Every shot id starts with your reel id. Your first
shot starts exactly at your reel's `at` (`web/timeline.js`). Scratch goes in `notes/work/<reel>/`.

## Working together
- **Shared code is the director's.** Found a bug in `web/lib/*`, `shared.js`, `render/*`? Work around it in your own
  file, send the EXACT fix to `main`, and add it to `notes/BUGS.md`. The director merges and broadcasts.
- **Pictures**: if one is truly missing, send `main` a precise request (what for, composition, who, mood, size, when).
  Keep painting with a placeholder meanwhile; don't wait.
- **Clips** (if the film has them) arrive while you work, usable at once as scaled frames. Until yours lands, paint
  with its first frame as a still: `'file:notes/clips/ff/<clip>.png'`.
- **Hand-offs**: your first frame follows your neighbour's last. For a match cut, message that painter directly
  (`notes/CREW.md` lists the agent ids) and pass EXACT coordinates (the pupil at 960,480).
- **Send the director a first preview of your reel the moment it plays end to end**, even rough: notes are cheapest
  early. When the user tells YOU something directly, add it to `notes/NOTES.md` verbatim and tell `main`.

## The machine
One shared PC. Be light: stills at `--w 960`, one preview at a time, close browsers. The render slots
(`notes/.render-slots`) are shared by everyone: "waiting for a slot" is normal.

## The absolute rules
- **No song lyrics anywhere**: not on screen, not in code, comments, reports or messages.
- **Never the user's name or handle on screen.** Credit exactly what the film's credit says, nothing else.
- Pure functions of time. Declare every asset and every clip frame. Your file only.
- (the film's own: the reserved colour and its owner, what must never be cute, what is never shown, the content limits)
