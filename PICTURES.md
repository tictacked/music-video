# PICTURES: making them, keeping the cast consistent, the traps, cut-outs

Pictures are the film's raw material: the cast as cut-outs (figures on flat ground, cut out and composited by the
engine), plates (places, used whole), props and UI pieces. Painters build shots from them; the engine gives them motion
(camera moves, parallax, boil, squash, transitions). An images-only film can be the best film.

## Which generator
Ask the user what they use, and follow them.
- **NovelAI (by hand).** NovelAI's terms require every generation to be started by a person, so the kit never calls
  it by itself. The workflow:
  1. `python tools/assets.py` writes the job lists.
  2. `python tools/promptsheet.py` writes `notes/prompts.html`: each job's prompt, negative, size, character
     prompts with positions, reference picture, copy buttons, and how many pictures it has so far.
  3. The user generates in NovelAI, keeps the ones they like, and saves them (PNG, as downloaded) into
     `assets/inbox/`.
  4. `python tools/intake.py` files each picture under its job by reading the prompt stored inside the PNG.
  5. `<PY> tools/cutout.py`.
  It keeps the user's own tools and taste in the loop (picking favourites, inpainting a hand, re-rolling a face).
- **A local Stable Diffusion WebUI** (AUTOMATIC1111, Forge, reForge, SD.Next) started with `--api`:
  `python tools/gen.py --jobs tools/jobs/cast.json` generates the jobs itself, as a guest (it never changes the
  WebUI's settings unless you pass `--switch`). The recipe (model, sampler, steps, cfg, quality words, LoRAs) goes
  in film.json `pictures`; the address is the kit's `machine.json` `a1111`.
- **Anything else** (another web generator, commissions, the user's own drawings): save into
  `assets/inbox/<job>/` and `python tools/intake.py` files them by folder.

## NovelAI Diffusion V5: what matters here
- **Transparent backgrounds**: prompt `transparent background` (or `has alpha`) and the PNG comes back see-through
  (verified: a clean full-figure alpha). For figures to cut out, this beats the flat-ground trick: `cutout.py` uses the
  picture's own alpha when it has one. In `tools/assets.py` set `GROUND = ALPHA`. Check the edges at 100% (hair
  wisps, glows) on the first few.
- **Prompting V5 well** (what heavy users' PNG metadata shows, and what held up in tests):
  - STYLE in the base prompt, the CHARACTER in a Character Prompt, even for one person (centred; positions off).
    The look stops fighting the character.
  - Numeric weights: `1.3::oekaki::`, `2::solo::`; NEGATIVE weights inline: `-1::simple background::` pushes a
    trait away without touching Undesired Content. Braces `{tag}` / brackets `[tag]` still nudge up / down.
  - Medium stacks carry a look (`sharp watercolour`, `graphite (medium)`, `tegaki`, `oekaki`, `no lineart, no
    outline`, `screen print`); plain mood words work (melancholic, liminal space); a year tag (`year 2010`) plus
    `visual novel, game_cg` pulls an era's CG look.
  - A graphic, inked look with no reference at all: `1.4::flat color::, 1.3::thick lineart, bold outlines::, limited
    palette, high contrast, cel shading, graphic illustration, pop art, screen print, 1.2::dynamic pose::, dutch angle,
    colored background, -1::gradient, soft shading, 3d, realistic::`. No reference means no colour leak.
  - Two V5 models: Full (`nai-diffusion-5-full`) and Curated (`nai-diffusion-5-curated`); Curated with `no lineart`,
    DPM++ 2S Ancestral and CFG rescale 1.0 gives flat-shape poster looks. 23-28 steps and CFG 5 are the usual.
  - **A palette declaration holds a film's colour rule**: `limited palette: white, red and black` in the character
    prompt (with a pen texture in the base: `1.6::faux traditional media, oekaki, sketch, crosshatching::`, and
    `-1::simple background::`) kept every picture to those three colours. Put it in the CHARACTER prompts: declared
    only in the base, it loses to the characters' own colours. Mood words beside it (liminal space, world of nothing,
    farewell, dutch angle) make a whole look out of empty space.
  - **Titles and signs in the picture**: end the prompt with `Text: THE TITLE` and turn NovelAI's quality toggle OFF
    (V5's quality tags add "no text"). It handles Japanese too. In a busy scene, ask for "large bold title typography
    at the top".
  - **Many characters in one frame**: one Character Prompt each, placed left to right (x 0.1-0.9). Seven held with no
    bleed; two identical twins were told apart by their outfits alone.
  - **A whole manga page in one generation**: describe the layout in plain language ("Panel 1, a wide panel across the
    top: ... Panel 2, middle left: ...") plus `Text: <the line>`, and it letters the line into a speech bubble.
  - **Same seed + same character prompts = the same staging** in a completely different world (only the base prompt
    changes): a film can switch looks per section and keep its blocking.
  - NovelAI also hides a copy of the settings in the alpha channel, so even a re-saved PNG may still carry its prompt.
- **What V5 is like next to a LoRA-trained local model** (measured on one seed each): it follows prompts more
  literally (outfits, hair length, "standing straight"), its default look is cleaner and softer with more atmospheric
  light (backgrounds are a strength), and its poses are calmer; a LoRA trained on the user's art keeps more of their
  graphic attitude. "pink background" came back hot magenta: fine for keying.
- **Character prompts with positions**: one prompt per character, placed on the canvas; V5 follows the positions
  closely and bleeds much less between characters (hair, eyes, clothes swapping between people is the classic
  two-shot failure). The job's `chars` list carries them; the prompt sheet shows each with its place.
- **Natural language and tags both work** (English and Japanese officially). Quoted text renders as text in the
  picture: good for a sign or a phone screen, but check every letter.
- **Precise Reference and Vibe Transfer were not in V5 at launch** (checked against the live API a month later: both
  still failed on V5). Until they are: consistency rides on the character block in every prompt, and reference jobs
  run on **V4.5**:
  - **Vibe Transfer = a STYLE reference.** Give 1-3 pictures in the look the user wants (their art, or earlier film
    pictures): V4.5 borrows the line, the colour handling, the poses' attitude, even the grounds' graphic shapes. It
    ALSO leaks the references' colours and features (a tan, green-haired reference turned a pale, brown-haired
    character tan and green-haired). Lowering the strength or the information extracted did NOT stop the leak;
    naming the character's own colours in the prompt (and the reference's in the negative) did. Prompt controls the
    leak, not weight. Costs a few Anlas per reference.
  - **Precise Reference ("character & style") = a CHARACTER reference** that keeps a design (face, hair, outfit) and
    takes some of the style; it doesn't bring the pose's attitude. About 5 Anlas a picture.
  - A reference picture should be clean: one character, their canonical outfit, no text.
- V5 Full has inpainting at launch; V5 Curated uses V4.5's.
- Sizes and cost: on the Opus tier, normal sizes (about 1 megapixel or less) at 28 steps or fewer, one picture at a
  time, cost no Anlas. The kit's sizes stay inside that: 832x1216 figures, 1216x832 landscapes, 1344x768 plates
  (close to 16:9: crop to 1344x756, the engine scales it up), 1024x1024 squares. NovelAI shows the cost on the
  Generate button: if it isn't free, the size or steps are over.

## Making them: the job list (tools/assets.py)
- ONE character block per person (who, hair, eyes, build, outfit, props) + ONE negative block (the colours and features
  that must never drift onto them). **Put the outfit in EVERY prompt**: without it, clothes wander or vanish.
- **Describe a character from the user's pictures of them, never from the archetype the card's words evoke** ("gruff
  old sailor" drew a cartoon pirate; the user's drawing was a lean, tired man in a pea coat).
- Order: whatever gates the next stage first (clip first frames before the cast; the cast in REEL order; plates for
  the first reels first). Spawn painters before the last pictures arrive: they build with placeholders meanwhile.
- **Figures to cut out**: full body, wide shot, feet visible, on `transparent background` (NovelAI V5) or a FLAT
  SATURATED ground (mint by default; pink or sky if the figure wears mint). Never white, cream, black or red: the
  mattes fail.
- Review every sheet (`assets/gen/<job>/_sheet.jpg`) before a painter touches it; show the user labelled sheets and
  treat every picture they don't flag as a pick. `tools/pickboard.py` puts several jobs' candidates on one board.

## Keeping a cast consistent
- **Try prompting first.** A careful character block, the same words every time, often holds a character across a
  whole film. Run a small bake-off first (2 seeds x 3 shots from the story, one sheet), show the user, and only go
  heavier if nothing holds them.
- **Heavier options**: a reference feature (NovelAI Precise Reference on V4.5; IP-Adapter or a reference ControlNet on
  a local WebUI), or, locally, a small LoRA trained on 15-30 of the user's pictures of the character. For a LoRA, the
  captions must NAME the character, and whatever the captions leave undescribed binds to the trigger word: a
  signature on every training picture becomes a signature on every output; a striking accessory on only a few of them
  shows up on strangers. Salience beats prevalence.
- **One hand for a whole cast**: when characters come from different sources and look drawn by different people,
  redraw the keepers through ONE model by img2img at ~0.6 (keeps the pose, swaps the hand). A lineup at true heights
  shows mismatches that per-character sheets hide.
- **A look only one model can draw**: draw it there, then redraw through the cast's model at ~0.5. Two steps beat any
  prompt.
- **Character sheets**: a TURNAROUND in one wide pass ("multiple views, character turnaround, reference sheet, front
  view, side view, back view") and an EXPRESSION CHART the same way. Charts blush everyone: negative "blush,
  flustered, nervous".
- **Face inpaints on one base picture** give a whole set of expressions with the same everything else (mask the face;
  padding ~48, blur ~10, strength 0.6-0.8).
- A model's "aesthetic" finetune may be prettier and drift off-model (longer, messier hair; generic faces; a new prop
  in the wrong colour). Test it on the cast before switching.

## Prompt recipes and traps (each one cost a film something)
- **Faces too comic** (a "shocked / crying / wide eyes" prompt gives round O_O faces, and dark stories go cute):
  prompt a THRILLER grammar (tools/assets.py `HITCHCOCK`: high or low angles, harsh light and deep shadow, hollow
  half-lidded eyes) + the `NOT_COMIC` negative.
- **Hiding a face**: `BACK_VIEW` + the `NO_FACE` negative. Think about how a pose READS: a figure bent over seen from
  behind can read as something else entirely; the fix may be the front view with the face just visible.
- **Wide canvases grow twins**: `ANTI_TWIN` in the negative.
- **Two-shots bleed** (hair, eye and skin colour, uniforms swap between people; sometimes a kiss the story never had):
  character prompts with positions (NovelAI), each character's colours named on the right person, a negative on the
  bleed ("kiss, kissing" up front), every picture checked; composite two singles when all fail; better still,
  shot / reverse-shot.
- **Groups**: paint every member ALONE and composite (group prompts come out childish). Figures sharing a frame need
  ONE ground: height from depth x real height + a contact shadow (floating figures are the first thing people notice).
- **Model habits**: most anime models sit people down (img2img the one standing picture), turn faces to the camera,
  and read "her right eye" as IMAGE-right (asymmetric features land on the wrong side: mirror at cut time and check
  by eye beside the reference).
- **Word traps**: "crown" (of the head) draws a crown; "rosary wound around her fingers" draws chains; "shadowed eyes"
  invites hair over one eye; "questioning" draws floating question marks; "floppy" defeats "ears standing up" (use a
  negative instead); "alien" draws the film franchise; swimwear invites cheesecake poses even with negatives. A
  garment the model keeps shortening needs weight: `(long skirt:1.4)` (A1111) or `1.4::long skirt::` (NovelAI).
- **Hands can't be posed by text**: draw a flat palm SILHOUETTE and img2img it at ~0.5.
- **The crown trap**: a picture whose figure touches the TOP edge (a "cowboy shot" crop) keeps that cut everywhere it
  goes (every clip made from it, every zoom). Check each cut-out's top row; pad the picture onto its own ground and
  inpaint the missing crown (`tools/crownpad.py` + a mask) rather than generating into an empty band (it grows a
  second face).
- **img2img strengths**: ~0.70 keeps the pose and swaps the person; ~0.55 leaks the source's clothes; ~0.45 of a
  picture into its own twin changes only the light (a time-of-day dissolve).
- A new side character is designed for CONTRAST with the lead (hair, headwear, colours) and never wears the reserved
  colour.
- Pillarboxed or letterboxed pictures happen (some models learned 4:3 frames): `BARS` in the negative;
  `<PY> tools/unbar.py` moves barred pictures out so they can be re-rolled.

## Story in the picture
- **Eye contact is story.** Check every shot's gaze against who knows what: a character looking into the lens during a
  "recording" shot reads as "she knows she's being filmed". In an obsessive's point of view, the one they watch never
  looks at the camera, because the camera IS the obsessive.
- Check every hero picture against the story's limits (clothes stay on; tears only where canon allows them; nothing
  that sexualises anyone young or young-looking).
- Real places from real photos: `<PY> tools/photos.py` (Wikimedia Commons, licences kept in `sources.json`), then
  img2img into the film's look (strength ~0.3 keeps sign lettering legible, ~0.45 paints more, ~0.6 mostly invents).
  Generated lettering is gibberish: keep only words that real signs have, and smear or repaint the rest.
- A sketched character in a colour world: `tools/pencil.py` (a pencil twin with the exact pose and eyes of a colour
  picture) and `tools/sketchcut.py` (a sketch as a PAPER cut-out, keyed into a colour plate). Everything must TOUCH the
  world: ground planes from the feet, contact shadows, dust, and every effect takes the figure along with the picture.

## Cut-outs (`<PY> tools/cutout.py`)
- A picture with real transparency keeps its own alpha. Otherwise rembg `isnet-anime` (about 1 s a picture on the CPU)
  + a clean-up that keeps the largest figure blobs, then `demint` keys the mint left in hair gaps, then
  `tools/retouch.py` applies per-picture fixes (a repainted neck, a covered stray mark) so every reel gets them.
- Never cut: film.json `nocutPrefixes` (plates `pl_`, first frames `ff_`, img2img tests `i2i_`) and `whole`. ONE list,
  read by cutout.py AND the page's cast.js. `DT.cast.pick()` only returns pictures whose cut-out exists.
- `keycut` jobs get a matte from the flat ground instead (`tools/holekey.py`): big-headed chibis rembg mattes away,
  vehicles and objects (rembg only cuts figures), red blades and sprays rembg strips.
- rembg keeps flat ground inside enclosed gaps (between an arm and the body): `holekey.py` keys ground-coloured holes.
- A colour rule needs hygiene tooling that runs automatically and is sampled, not eyeballed: a reserved red drifts
  into warm plates under a grade; a loose red mask turns deep auburn hair purple (re-roll with the colour in the prompt
  instead of recolouring hair). Check thin hair blends at 100% after any despill.
- **Rebuild the manifest after the LAST picture batch** (`cutout.py --manifest`): the pick helpers silently fall back
  to another picture when a pick isn't in the manifest yet, so a render made before the rebuild shows the OLD pictures
  with no error.
- Swapping a picture IN PLACE (same job and number, the original kept in `notes/work/_orig_*`) updates every reel with
  no code change. Then rebuild the manifest.
