const { chromium, expect } = require('../frontend/node_modules/@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const app = process.env.APP_URL || 'http://127.0.0.1:5180';
  const out = path.resolve(process.env.BROWSER_OUTPUT_DIR || 'test-results/landing-browser');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 810 } });
  const errors = [], apiRequests = [], externalRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    const url = new URL(request.url());
    if (/\/(api|health)(\/|$)/.test(url.pathname)) apiRequests.push(request.url());
    if (/^https?:$/.test(url.protocol) && url.origin !== new URL(app).origin) externalRequests.push(request.url());
  });
  try {
    await page.goto(app + '/');
    await expect(page.locator('html')).toHaveAttribute('data-ready', 'true');
    await page.evaluate(() => document.fonts.ready);
    await expect(page.getByRole('heading', { name: 'Written to sell. Judged on evidence.' })).toBeVisible();
    if (apiRequests.length) throw Error('Welcome page called the backend');
    await expect(page.locator('.nav a')).toHaveCount(1);
    await expect(page.locator('.eyebrow')).toHaveCount(0);
    if (await page.locator('.hero-cta').evaluate(node => getComputedStyle(node).backgroundColor) !== 'rgb(56, 59, 64)') throw Error('Entry button is not dark gray');
    if (await page.locator('.card').count() !== 6) throw Error('Missing advertising examples');
    const expectedImages = ['domestic-abuse', 'social-ethics', 'shock-imagery', 'religion', 'animal-ethics', 'sexual-innuendo'];
    await expect.poll(() => page.locator('.ad-image').evaluateAll(images =>
      images.length === 6 && images.every(image => image.complete && image.naturalWidth > 0)
    )).toBe(true);
    const imagePaths = await page.locator('.ad-image').evaluateAll(images => images.map(image => new URL(image.currentSrc).pathname));
    if (JSON.stringify(imagePaths) !== JSON.stringify(expectedImages.map(name => '/landing-ads/' + name + '.webp'))) throw Error('Incorrect supplied advertising images');
    if (await page.locator('.ad-image').evaluateAll(images => images.some(image => getComputedStyle(image).objectFit !== 'contain' || !image.alt))) throw Error('Images are cropped or lack descriptions');
    if (await page.locator('.ad-image').evaluateAll(images => images.some(image => {
      const box = image.getBoundingClientRect();
      return Math.abs(box.width / box.height - image.naturalWidth / image.naturalHeight) > 0.01;
    }))) throw Error('Card proportions do not match the source images');
    if ((await page.locator('.cards').textContent()).trim()) throw Error('Old decorative copy covers the advertising');
    const loaded = await page.evaluate(() => [
      document.fonts.check('400 20px Inter'), document.fonts.check('400 20px Newsreader'),
      document.fonts.check('italic 400 20px Newsreader'), document.fonts.check('500 12px "IBM Plex Mono"'),
    ]);
    if (loaded.includes(false)) throw Error('Embedded fonts did not load');
    await page.getByRole('button', { name: 'Pause motion', exact: true }).click();
    const before = await page.locator('.card.home').evaluate(node => getComputedStyle(node).transform);
    await page.waitForTimeout(200);
    if (before !== await page.locator('.card.home').evaluate(node => getComputedStyle(node).transform)) throw Error('Pause did not stop the belt');
    const hero = await page.locator('.hero h1').boundingBox(), scanner = await page.locator('.scan').boundingBox();
    if (Math.abs(hero.x + hero.width / 2 - 720) > 1 || Math.abs(scanner.x - 720) > 1) throw Error('Hero/scanner not centered');
    await page.screenshot({ path: path.join(out, 'desktop-1440.png') });
    const belt = page.locator('.belt');
    await belt.focus();
    await page.keyboard.press('ArrowRight');
    if (before === await page.locator('.card.home').evaluate(node => getComputedStyle(node).transform)) throw Error('Keyboard scrub did not work');
    const beforeDrag = await page.locator('.card.home').evaluate(node => getComputedStyle(node).transform);
    const box = await belt.boundingBox();
    await page.mouse.move(800, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(960, box.y + box.height / 2, { steps: 12 });
    await page.mouse.up();
    if (beforeDrag === await page.locator('.card.home').evaluate(node => getComputedStyle(node).transform)) throw Error('Reverse dragging did not rebuild the card');
    const topics = new Set();
    for (let i = 0; i < 100; i++) {
      await belt.focus(); await page.keyboard.press('ArrowLeft');
      topics.add(await page.locator('.badge-topic').textContent());
    }
    if (topics.size !== 6) throw Error('Example indicator does not follow all six cards');
    if (externalRequests.length) throw Error('Welcome page requested external resources: ' + externalRequests.join(', '));
    for (const [width, height] of [[1703,955], [890,902], [740,955], [390,844], [320,568]]) {
      await page.setViewportSize({ width, height });
      await page.waitForTimeout(150);
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw Error('Horizontal overflow at ' + width);
      const cta = await page.locator('.hero-cta').boundingBox(), badge = await page.locator('.badge').boundingBox();
      if (cta.y + cta.height > badge.y) throw Error('Hero overlaps scanner counter at ' + width);
      await page.evaluate(() => document.activeElement.blur());
      await page.screenshot({ path: path.join(out, `welcome-${width}.png`), fullPage: true });
    }
    await page.setViewportSize({ width: 1440, height: 810 });
    await page.getByRole('link', { name: 'Open the court', exact: true }).click();
    await expect(page).toHaveURL(/\/review$/);
    await expect(page.getByRole('button', { name: '项目与素材', exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('button', { name: '项目与素材', exact: true })).toBeVisible();
    await page.getByRole('button', { name: '数字人像测试', exact: true }).click();
    await expect(page).toHaveURL(/\/jury/);
    await expect(page.getByRole('heading', { name: '数字人像测试', exact: true })).toBeVisible();
    await page.getByRole('button', { name: '项目与素材', exact: true }).click();
    await expect(page).toHaveURL(/\/review$/);
    for (const version of ['v1', 'v2', 'v3']) {
      await page.goto(app + '/?ui=' + version);
      await expect(page.locator('#root')).not.toBeEmpty();
      if (await page.locator('.hero').count()) throw Error('Legacy alias shows welcome page');
    }
    const offline = await browser.newPage({ reducedMotion: 'reduce', viewport: { width: 1440, height: 810 } });
    await offline.route('**/*', route => {
      const url = new URL(route.request().url());
      return url.origin === new URL(app).origin ? route.continue() : route.abort();
    });
    await offline.goto(app);
    await offline.evaluate(() => document.fonts.ready);
    await expect.poll(() => offline.locator('.ad-image').evaluateAll(images =>
      images.length === 6 && images.every(image => image.complete && image.naturalWidth > 0)
    )).toBe(true);
    await expect(offline.getByRole('button', { name: 'Play motion', exact: true })).toBeVisible();
    const still = await offline.locator('.card.home').evaluate(node => getComputedStyle(node).transform);
    await offline.waitForTimeout(250);
    if (still !== await offline.locator('.card.home').evaluate(node => getComputedStyle(node).transform)) throw Error('Reduced motion is not static');
    await offline.locator('.belt').focus();
    await offline.keyboard.press('ArrowRight');
    if (still === await offline.locator('.card.home').evaluate(node => getComputedStyle(node).transform)) throw Error('Reduced-motion manual scrub unavailable');
    await offline.screenshot({ path: path.join(out, 'offline-reduced-motion.png') });
    await offline.close();
    if (errors.length) throw Error(errors.join('\n'));
    console.log(JSON.stringify({ welcome: 'no backend calls or external requests; embedded fonts, 6 supplied images, centered gray scanner, pause, keyboard and drag passed', exampleTopics: [...topics], routes: '/ -> Open the court -> /review -> /jury -> /review; version aliases passed', responsiveWidths: [1703,1440,890,740,390,320], offlineAndReducedMotion: 'all images loaded, passed', pageErrors: errors }));
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
