# SONG: from the audio to song/timing.json (and how to cut to it)

## Getting the song in
- Put the audio in `song/` as `audio.wav` (analysis) and `audio.m4a` (what the master muxes: film.json `audio`):
  `ffmpeg -i "<source>" song/audio.wav` and `ffmpeg -i "<source>" -c:a aac -b:a 256k song/audio.m4a`.
- **A song the user made with an AI music service** (Suno and the like): the mp3's tags often carry the lyric sheet
  and the title: `ffprobe -v error -show_entries format_tags -of default=nw=1 song.mp3`. Its embedded cover art
  (`ffmpeg -i song.mp3 -an -frames:v 1 cover.png`) and the user's canonical picture of the character make good payoff
  moments used as themselves.
- **A commercial song**: its words never leave `song/private/`.
  - They go nowhere else: not on screen (not even a translation), not in timing files, code, comments, briefs,
    messages, or your replies to the user.
  - Lyric TEXT anywhere a painter can read it can trip the API's output filter ("Output blocked by content filtering
    policy") and kill the painter mid-reel.
  - Whisper's word tokens ARE the lyrics: write word TIMES only (an index per word), and keep any transcript in
    `song/private/`.
  - Write gists as loose descriptions (never near-verbatim), and name moments by hook number or by what happens
    (`hooks[3]`, "the first drop").
  - Tell every painter the rule.
- A song's length decides a lot: a 90 s TV-size cut is a very different job from a 4-minute album track. If the user
  is open to it, a shorter edit is a real option (ffmpeg can cut on a bar line; crossfade 30-80 ms).

## The kit's pipeline (the film's song/ folder; <PY> = `python tools/film.py PY`, <SEP> = `python tools/film.py SEP`)
1. `song/audio.wav` + `song/audio.m4a`.
2. `<SEP> song/separate.py`: Demucs htdemucs on the CPU (~30 s for a 2:30 song on a modern CPU) into
   `song/stems/{drums,bass,other,vocals,band}.wav` (band = everything but the vocals).
3. `<PY> song/analyze.py`: the drum-attack grid (film.json `bpmHint` starts the tempo search; a DAW production is one
   straight line of beats), the downbeat phase, per-bar loudness per stem, accents, kicks and snares from the DRUM stem
   (on the full mix, vocal plosives read as ghost kicks), and stops.
4. `song/sections.json` by hand: the section map, TIMES ONLY, with a `story` line per section once the storyboard
   exists, and the stops you've checked:
   `{"sections": [{"id": "intro", "bars": "0-3", "t0": 0.0, "t1": 8.1, "story": ""}, ...], "stops": [[61.2, 63.4]]}`.
   `bars` is the section's bar range in the B<n> numbering of analyze.py's bar table ("0-3", "12"); a pickup before
   bar 0 is "-1" or "-1-0". `t0`/`t1` are seconds and are what the engine uses.
   analyze.py's printout (the bar table, the vocal phrases, the stops it found) is the starting point. Measure with
   `<PY> song/ear.py T0 T1` (the vocal stem's loudness per sixteenth, plus onsets: the measuring tape for everything)
   and, for an instrumental, `<PY> song/listen.py`. analyze.py and timing.py need the stems from step 2.
5. `<PY> song/timing.py` -> `song/timing.json` + `web/timing.js`: bpm, beat0, barOffset (**B<n> = beat0 + (4n +
   barOffset) beats**: the anchor timeline.js and `render.mjs --from B7 --to END` use), sections, beats, kicks, snares,
   accents (onset strength normalised LOCALLY over +-3 s, or the choruses get none), vox (vocal phrase TIMES), stops,
   and per-frame envelopes. `lines` stays EMPTY.
- The grid assumes 4/4 bars. A 6/8 or 3/4 song needs checking: count a few bars by ear before trusting the anchors.
- A film longer than its song (a held last image, a silent tag): film.json `holdAfter` (seconds), and make
  `song/audio_hold.m4a` = the song + that silence (`ffmpeg ... -af apad=pad_dur=N`) and point `audio` at it.

## Words, when the timing needs them
- `<PY> song/words.py` (faster-whisper; `python <skill>/kit/setup.py --whisper` installs it): word and segment TIMES
  from the vocal stem, into `song/private/` only. It prints counts and times, never words. `--lang ja` for a
  Japanese song; `--prompt song/private/lyrics.txt` gives it the lyric sheet as a hint.
- Whisper hears maybe 70% of a sung song: backing-vocal parentheticals, asides in a second language and chants go
  missing, and it picks ONE language per file. Strip parentheticals before aligning; where the words fail, map lyric
  lines to its SEGMENTS in order (segment timestamps stay right even when the words are wrong); as a last resort, ask
  the user to tap the downbeats of a few lines.
- When it hears very little (an invented language, glitch syllables), SEPARATE THE VOCALS first: whisper on the stem,
  plus short windows prompted with the exact lyric beats the full mix. Then write a HAND WORD TABLE (every token's
  start, `~` = estimate, `u` = unsung) instead of trusting an aligner. The stems also show the real structure: a
  vocal-silent bar, a stage direction that is a real band cut, a lyric the recording skipped.
- Whisper's word STARTS run early: snap the words you cut on to the vocal stem's onsets (`song/ear.py`). Choruses of
  produced songs repeat on the exact bar grid, so a pin transfers +N bars (verify on the onsets).

## Instrumentals
Measure the track's OWN vocabulary: the stems, the drum grid, and the band that IS the track's identity (a struck-metal
ring at a few kHz, a sub-bass drop, a vinyl crackle). Put it in `timing` as its own list (e.g. `DT.timing.metal`:
every cut, shake and stamp). Name the story's fixed moments in `timing.marks` (the title hits, the breath, the fade).
In a good instrumental AMV, instruments become actions: more than half the cuts land on onsets.
Demucs puts any lead melody (a synth, a sax, a whistle) into the vocal stem, so on an instrumental `vox` marks that
melody as "singing" (it can span the whole song). Check `vox` against the song and clear it in `song/timing.json`, or
use it knowingly as the melody's phrases.

## The song's structure is the story's structure
- **Time map before storyboard.** Print the per-second energy of the instrumental passages: the silences and drops are
  where the story's biggest beats go (a long silence becomes the moment everything stops; the bass coming back becomes
  something coming back to life). Map the RP's acts or loops onto the verse/chorus cycles, and put the deaths in the
  drops and silences.
- **Detect the STOPS before the storyboard** (the band stem under -42 dB for >= 0.25 s -> `DT.timing.stops`). A song
  whose band drops out dozens of times will organise the whole film around its silences (type alone on black, 1-bit
  freezes, hits on the band's RETURN).

## Cutting to it: what great videos measurably do
Measured on six videos (two fan AMVs, three K-pop MVs, one first-attempt story MAD) with a cut detector, a beat grid
and an eye-tracker proxy:
- **Cut pace follows the song's energy** in every professional video (correlation 0.23-0.59; the first-attempt MAD:
  0.04, which was its main flaw). Give each section a pace.
- **AMVs stutter** (13-25% of shots shorter than half a beat: symbol flickers, light strobes on drum fills); **K-pop
  holds** (29-44% of shots longer than 4 beats). Average shot: AMV 0.7-1.0 s, K-pop 1.7-1.9 s; the first-attempt MAD
  2.8 s.
- **Cut on onsets as well as the grid** (the K-pop videos: 57-63% of cuts on a sound in the mix; the first-attempt
  MAD: 19%).
- **Eye-trace**: the best MAD's cuts moved the eye 35% less than random pairs of shots (faces and eyes stay put
  through fast runs). Plan where each shot's subject sits at its start and end.
- Eyes as punctuation; one visual rule from the source's own metaphor (a grey world that turns to colour); a motif
  system with a bookend; a literal joke beside the melodrama; quote what the audience knows; colour by section;
  motion inside shots.
- **librosa's beat_track runs ~27 ms LATE and onset_detect ~20 ms** (measured on a click track): every professional
  video first measured as "cutting 1 frame early", which was that lag. Corrected, the pros cut ON the beat, so
  frame-exact is right. (An analyser that stamps STFT frames at the window START puts its whole grid ~1 frame early.)

## When a note says a shot doesn't hit the drums
MEASURE the drum stem in bands over the shot (7-16 kHz = hats and cymbals, 1.5-5 kHz = snare, 30-120 Hz = kick), hand
the painter frame numbers, and have it prove the fix from the rendered preview: the per-frame picture change peaks on
exactly those frames.
