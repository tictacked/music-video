// browser.mjs -- the one place the renderers launch headless Chrome (render.mjs, stills.mjs, check_assets.mjs; the
// kit's test/regress.mjs and setup.py's check too). The page needs WebGL2 on every platform, with a GPU or without:
//   win32   ANGLE on Direct3D 11 (the GPU)
//   darwin  ANGLE on Metal (the GPU)
//   linux   the GPU if Chrome can use one
// Every launch PROBES WebGL2 first (a draw and a read-back, ~1 s). If the GPU path is dead (a machine with no usable
// GPU: Chrome then hands out contexts that are already LOST, and every frame renders blank), it relaunches with
// SwiftShader, Chrome's software WebGL: slower, the same pictures. The choice is remembered for the rest of the process.
// MV_CHROME_ARGS (space-separated) replaces all of this when set (no probe, no fallback), e.g. for a root container:
//   MV_CHROME_ARGS="--no-sandbox --use-angle=swiftshader --enable-unsafe-swiftshader"
// Only compare frames rendered with the same flags: GPU and software frames look alike but aren't bit-identical.
//
//   import { launch } from './browser.mjs';
//   const browser = await launch();               // extra: more puppeteer.launch options; extra.args are appended
import puppeteer from 'puppeteer';

const DEFAULTS = {
  win32: ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=d3d11'],
  darwin: ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=metal'],
  linux: ['--enable-gpu', '--ignore-gpu-blocklist'],
};
export const SOFTWARE = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'];
let chosen = null;          // the flags that passed the probe in this process

export function chromeArgs() {
  const env = process.env.MV_CHROME_ARGS;
  if (env !== undefined) return env.split(' ').filter(Boolean);
  return chosen || DEFAULTS[process.platform] || DEFAULTS.linux;
}

// 'ok', or why WebGL2 can't draw in this browser
async function probe(browser) {
  let page;
  try {
    page = await browser.newPage();
    return await page.evaluate(async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const c = document.createElement('canvas'); c.width = 1920; c.height = 1080; document.body.appendChild(c);
      const gl = c.getContext('webgl2', { preserveDrawingBuffer: true });
      if (!gl) return 'no WebGL2 context';
      await wait(250);
      if (gl.isContextLost()) return 'the context was lost at start';
      gl.clearColor(1, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT);
      const px = new Uint8Array(4); gl.readPixels(960, 540, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      await wait(150);
      if (gl.isContextLost()) return 'the context was lost after a draw';
      return px[0] > 200 && px[1] < 50 ? 'ok' : 'a draw read back as ' + Array.from(px).join(',');
    });
  } catch (e) {
    return 'the probe failed: ' + e.message;
  } finally {
    if (page) await page.close().catch(() => {});
  }
}

export async function launch(extra = {}) {
  const opts = (args) => ({ headless: true, ...extra, args: [...args, ...(extra.args || [])] });
  if (process.env.MV_CHROME_ARGS !== undefined) return puppeteer.launch(opts(chromeArgs()));
  const tries = chosen ? [chosen] : [DEFAULTS[process.platform] || DEFAULTS.linux, SOFTWARE];
  let why = '';
  for (const args of tries) {
    const browser = await puppeteer.launch(opts(args));
    const r = await probe(browser);
    if (r === 'ok') {
      if (!chosen && args === SOFTWARE) console.log(`(no working GPU WebGL here: ${why}; rendering with SwiftShader, software WebGL: slower, same pictures)`);
      chosen = args;
      return browser;
    }
    why = r;
    await browser.close().catch(() => {});
  }
  throw new Error(`headless Chrome has no working WebGL2, not even in software (${why}): see MACHINE.md`);
}
