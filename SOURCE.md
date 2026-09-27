# SOURCE: the RP or the OCs, read all the way through

## A SillyTavern roleplay
- Find it: `python <skill>/rp2txt.py --find <character or chat name>` (newest first, with message counts) or
  `--grep "a line you remember"` (searches every message). SillyTavern is found by itself in the usual places; if
  not, `--st <its folder>` or the `ST_DATA` environment variable. Exported files work too: a chat exported as
  `.jsonl` from the chat menu, and the character card exported as `.png`.
- Export it into the film:
  `python <skill>/rp2txt.py "<chat.jsonl>" --out notes/chat.txt --card "<card name or .png>" [--world <lorebook>]`
  - `notes/chat.txt`: every active message (swipes skipped) as `##### [n] Name (user)  date`. Everyone cites
    messages by `[n]`; each painter gets a message RANGE.
  - `notes/card.md`: the card (creator notes, description, personality, scenario, greetings, examples), every
    embedded lorebook entry, a standalone lorebook with `--world`, and the user's persona description (matched by the
    persona name in the chat, or `--persona`).
- **Read ALL of it before planning**, not a summary. The film lives in the details: a line the user wrote at [212], a
  prop that recurs, the joke they kept making.
- **Status boxes are DATA.** An RP that prints `Day 3, evening | HP 40/50 | Location: the old mill | Mood: wary` every
  turn has given you a clock: put it in `DT.STATE` (`[songTime, patch]` rows the engine applies in order; scenes read
  `ctx.state`; K.s.hud / K.s.status draw it). Painters read `ctx.state`; they never invent the state. The lorebook's
  geography is the map; the lorebook often holds endings and backstory the chat itself skipped.
- **The user's persona's messages are the user's own writing**: the gold. Quote them (typos fixed), never invent
  dialogue for anyone, and never credit the persona unless the user wants it.
- A group chat or a long campaign: pick the arc the song can carry (a 3-minute song holds about three acts), and say
  what's left out.

## OCs without an RP
Their pictures (the user's own art, commissions, generator keepers: ask which ones are CANON and which are jokes or
drafts), their card or profile, the user's own words about them. Ask for each character's non-negotiables: the look
that must hold (hair, eyes, build, outfit), what they'd never do, which version or AU the film is. A character's
canon beats the storyboard: if canon says he never smiles at strangers, he doesn't, even where the story would have
him.

## A remake of an old video
Read the original frame by frame first (a frame every 3 s as a contact sheet: `<PY> tools/contact.py old.mp4 --fps 0.33`),
and keep its
beats, cards and lines as homage where the user wants them. The remake is a conversation with the old one.

## Who are they, really? (PLAN.md)
Before any storyboard, for each lead: what they want, what they hide, what they do when nobody's watching. ONE
sentence, then ONE image that shows it. Pitch it to the user and let them confirm or correct it: they wrote these
people, and the film is only as good as this read. Every flashy device later must say something about it (CREW.md).
When the user asks "what are they really like?" mid-build: read the card and the character's own lines, pitch a
one-line truth, let the user confirm, storyboard a beat table (time / shot / what it says), then build.

## THE RULE
One visual rule, taken from the source's OWN metaphor, strong enough to carry the whole song:
- a colour that belongs to one person (the rest of the world is grey or ink);
- a lighthouse beam as the only light, so the lead exists only when it passes;
- paper cut-outs, and the one who lies has a white edge showing;
- the chat window as the set, which the story breaks out of at the end.
A period medium or a borrowed form can carry a mood (silent-film intertitles for a melodrama, an 8mm home movie for a
memory, a trading-card duel for a rivalry). The reserved colour and its owner go in film.json `reservedColour`;
`final_check.py` lists every second it's on screen, so nobody else wears it by accident.

## The image bank (STORYBOARD.md)
The source's own metaphors as pictures, each with its message number: "the snow globe she shakes at [88]", "the
promise ring at [140]". Painters draw from it; an images-only film runs on it. The best shots are almost always a
metaphor the user already wrote.

## Credits
The film's one credit line is film.json `credit`. A card by someone else: credit its AUTHOR exactly as the card says
(read it at full resolution; a character name in another script loses letters at small sizes). The song: artist and
title, if the user wants a credit. The user: only if they ask.
