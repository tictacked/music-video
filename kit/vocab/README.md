# vocab/: film vocabularies worth keeping

Each film writes its own vocabulary in `web/lib/vocab.js` (K.v: the pieces its RULE needs, drawn in Canvas2D). When a
piece is worth reusing (a game textbox, a chat window, a card duel), copy that film's vocab file here under a short
name (`vocab/chatui.js`), with a header that lists each piece, its signature, and anything film-specific to rewrite.

To reuse one: copy it into a new film's `web/lib/`, add `<script src="lib/<file>.js"></script>` after `vocab.js` in
`web/index.html`, and give each piece a testcard page before painters use it. A vocab file must stay deterministic:
time from `ctx`, randomness from seeds, never `Math.random()` or `Date`.
