// =============================================================================
// vocab.js -- K.v, THIS film's own vocabulary (Canvas2D; deterministic: anything random takes a seed / ctx).
// The film's look lives here: the motifs, cards and devices its storyboard needs that the kit (kit.js K.*, shaft.js
// K.s.*) doesn't have. Write each piece, list it below with its signature, add a testcard page for it
// (web/scenes/testcard.js), look at that page, THEN hand the piece to the painters.
// The film's own colours go here too: Object.assign(DT.pal, {...}) and DT.pal.who (speaker name -> colour).
// Rename the file (and K.v) after the film if you like; web/index.html loads it.
//
//   (the pieces, one line each: V.name(g, ctx, ..., {options})   what it draws)
// =============================================================================
(function () {
  'use strict';
  const DT = window.DT, K = DT.K;
  const V = (K.v = {});
  // V.example = function (g, ctx, x, y, o = {}) { ... };
})();
