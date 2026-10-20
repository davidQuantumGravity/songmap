import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition, openBrowser } from '@remotion/renderer';
import path from 'path';
const [,, id, ...frames] = process.argv;
const serveUrl = await bundle({ entryPoint: path.resolve('src/index.ts') });
const browser = await openBrowser('chrome', { browserExecutable: '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell', chromiumOptions: { gl: 'swangle' } });
const composition = await selectComposition({ serveUrl, id, puppeteerInstance: browser });
for (const fr of frames) {
  await renderStill({ composition, serveUrl, frame: Number(fr), output: `stills/${id}_${String(fr).padStart(4, '0')}.jpg`, imageFormat: 'jpeg', scale: 0.5, puppeteerInstance: browser });
}
await browser.close({ silent: true });
console.log('done');
