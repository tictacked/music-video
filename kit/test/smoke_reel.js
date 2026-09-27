// smoke_reel.js -- the kit's smoke-test reel. kit/test/smoke.py copies it into a scratch film as web/scenes/reel1.js.
// It touches every layer once: the testcard pages, a whole picture (a plate), a cut-out, a clip, a card, an RP line,
// looks, and several transitions. Anchors are bars of the synthetic song (120 BPM: a bar = 2 s; the stop is B6).
(function () {
  const { K, util: U } = DT, W = DT.W, H = DT.H, S = K.s;
  const clip = S.use('test', { from: 0 });
  DT.scene('smk_cast', {
    bg: '#f6f1e7',
    assets: ['cut:hero_full/1', 'gen:pl_room/1'],
    draw(g, ctx) {
      const plate = DT.img('gen:pl_room/1');
      if (plate) g.drawImage(plate, 0, 0, W, H);
      K.img(g, 'cut:hero_full/1', W / 2 + Math.sin(ctx.lt * 2) * 60, H - 40, { h: 900, anchor: 'feet' });
    },
    over(g, ctx) { S.say(g, ctx, 'hero', 'Every layer, once.', ctx.shot.start + 0.2, {}); },
  });
  DT.scene('smk_clip', {
    bg: '#000000',
    assets(ctx) { return [clip.key(ctx)]; },
    look() { return { grain: 0.06, vhs: 0.4 }; },
    draw(g, ctx) { clip.draw(g, ctx, { fit: 'cover' }); },
  });
  DT.scene('smk_card', {
    bg: '#0a0a0c',
    draw(g, ctx) { S.declare(g, ctx, 'SMOKE TEST', ctx.shot.start, { sub: 'the kit, end to end' }); },
  });
  DT.reel('reel1', [
    { id: 'reel1_type', scene: 'testcard', at: 0, params: { page: 'type' } },
    { id: 'reel1_card', scene: 'smk_card', at: 'B1', trans: { type: 'shatter', dur: 0.4 } },
    { id: 'reel1_cast', scene: 'smk_cast', at: 'B2', trans: { type: 'jigsaw', dur: 0.8 } },
    { id: 'reel1_clip', scene: 'smk_clip', at: 'B4', trans: { type: 'negflash', dur: 0.3 } },
    { id: 'reel1_stop', scene: 'testcard', at: 'B6', params: { page: 'shapes' }, trans: { type: 'static', dur: 0.3 } },
    { id: 'reel1_looks', scene: 'testcard', at: 'B7', params: { page: 'looks', look: { keepRed: 1 } },
      trans: { type: 'whip', dur: 0.3 } },
    { id: 'reel1_end', scene: 'smk_cast', at: 'B9', trans: { type: 'dissolve', dur: 0.5 } },
  ]);
})();
