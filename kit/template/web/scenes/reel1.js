// reel1.js -- PLACEHOLDER so a new film renders end to end on day one (the testcard for the whole song). Replace it with
// the storyboard's reels: one file per reel, owned by its painter, registered with DT.reel (see web/timeline.js).
(function () {
  DT.reel('reel1', [
    { id: 'reel1_type', scene: 'testcard', at: 0, params: { page: 'type' } },
    { id: 'reel1_shapes', scene: 'testcard', at: 4, params: { page: 'shapes' }, trans: { type: 'shatter', dur: 0.5 } },
    { id: 'reel1_looks', scene: 'testcard', at: 8, params: { page: 'looks', look: { keepRed: 1 } }, trans: { type: 'negflash', dur: 0.4 } },
  ]);
})();
