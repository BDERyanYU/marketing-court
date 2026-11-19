const { chromium, expect } = require('../frontend/node_modules/@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const backend = process.env.API_PROXY_URL || 'http://127.0.0.1:8021';
  const app = process.env.APP_URL || 'http://127.0.0.1:5180';
  const out = path.resolve('test-results/project-delete-paper-browser');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    await route.fulfill({ response: await route.fetch({ url: backend + url.pathname + url.search }) });
  });
  await page.route('**/health', async route => route.fulfill({ response: await route.fetch({ url: backend + '/health' }) }));
  try {
    const health = await (await page.request.get(backend + '/health')).json();
    if (health.mode !== 'demo') throw Error('Use isolated demo server');
    const demo = await (await page.request.post(backend + '/api/demo')).json();
    const name = '删除检查项目-' + Date.now();
    const target = await (await page.request.post(backend + '/api/projects', { data: { name } })).json();
    await page.goto(app + '/review');
    const open = page.locator('.sidebar-project').filter({ hasText: name });
    const trash = page.getByRole('button', { name: '删除项目：' + name, exact: true });
    await open.click();
    await page.getByRole('heading', { name, exact: true }).waitFor();
    await trash.click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await page.screenshot({ path: path.join(out, 'delete-confirmation.png') });
    await page.getByRole('button', { name: '取消', exact: true }).click();
    await expect(dialog).not.toBeVisible();
    await expect(open).toHaveCount(1);
    await trash.click();
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    let rejectOnce = true;
    await page.route('**/api/projects/' + target.project_id, async route => {
      if (route.request().method() === 'DELETE' && rejectOnce) {
        rejectOnce = false;
        return route.fulfill({ status: 409, json: { detail: '项目正在处理审核或生成内容，请等待完成后再删除。' } });
      }
      await route.fulfill({ response: await route.fetch({ url: backend + '/api/projects/' + target.project_id }) });
    });
    await trash.click();
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await expect(dialog.getByRole('alert')).toContainText('等待完成');
    await expect(open).toHaveCount(1);
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await expect(dialog).not.toBeVisible();
    await expect(open).toHaveCount(0);
    await page.reload();
    await expect(page.locator('.sidebar-project').filter({ hasText: name })).toHaveCount(0);
    if ((await page.request.get(backend + '/api/projects/' + demo.project_id + '/reviews')).status() !== 200) throw Error('Other project was removed');
    await page.getByRole('button', { name: '数字人像测试', exact: true }).click();
    const sample = await (await page.request.get(backend + '/api/jury/examples/copier-paper')).json();
    await page.getByRole('button', { name: '用复印纸样例', exact: true }).click();
    await page.getByRole('combobox', { name: '补充目标画像（可选）', exact: true }).waitFor();
    const original = page.getByRole('textbox', { name: 'A · 修改前', exact: true });
    const revised = page.getByRole('textbox', { name: 'B · 修改后', exact: true });
    await expect(original).toHaveValue(sample.original_text);
    await expect(revised).toHaveValue(sample.revised_text);
    await page.reload();
    await expect(original).toHaveValue(sample.original_text);
    await expect(revised).toHaveValue(sample.revised_text);
    await page.getByRole('spinbutton', { name: '测试人像数', exact: true }).fill('2');
    await page.getByRole('button', { name: '生成人像', exact: true }).click();
    await page.getByText('数字人像已保存，可以填写两版文案。', { exact: true }).waitFor();
    await page.reload();
    await expect(original).toHaveValue(sample.original_text);
    await page.getByRole('button', { name: '运行 A/B 盲测', exact: true }).click();
    await page.getByText('全部反馈已保存，可以查看配对结果。', { exact: true }).waitFor();
    await page.reload();
    await page.locator('#results').waitFor();
    const id = new URL(page.url()).searchParams.get('comparison');
    const result = await (await page.request.get(backend + '/api/jury/comparisons/' + id)).json();
    if (result.pairs.length !== 2 || result.exposures.length !== 4 || JSON.stringify(result.pairs).includes('水杯')) throw Error('Wrong paper results');
    for (const width of [320, 390, 740, 890, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw Error('Overflow at ' + width);
      await page.screenshot({ path: path.join(out, `paper-${width}.png`), fullPage: true });
    }
    if (errors.length) throw Error(errors.join('\n'));
    console.log(JSON.stringify({ deletion: 'cancel / escape / failure / retry / refresh / isolation passed', paper: 'report + exact A/B + generation + 4 feedbacks + refresh passed', widths: [320, 390, 740, 890, 1440], pageErrors: errors }));
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
