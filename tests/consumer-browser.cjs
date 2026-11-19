const { chromium } = require('../frontend/node_modules/@playwright/test')
const path = require('node:path')
const fs = require('node:fs')
async function main() {
  const app = process.env.APP_URL || 'http://127.0.0.1:5180'
  const backend = process.env.API_PROXY_URL || 'http://127.0.0.1:8021'
  const out = path.resolve('test-results/consumer-browser')
  fs.mkdirSync(out, { recursive: true })
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/jury/**', async route => {
    const url = new URL(route.request().url())
    await route.fulfill({ response: await route.fetch({ url: backend + url.pathname + url.search }) })
  })
  try {
    const health = await (await page.request.get(backend + '/api/jury/demo')).json()
    if (health.mode !== 'demo') throw Error('Use an isolated demo server')
    await page.goto(app + '/jury')
    await page.getByRole('button', { name: '用水杯样例', exact: true }).click()
    await page.getByRole('combobox', { name: '补充目标画像（可选）', exact: true }).selectOption('report')
    await page.getByRole('spinbutton', { name: '模拟成员数', exact: true }).fill('3')
    await page.getByRole('button', { name: '派生成员', exact: true }).click()
    await page.getByText('面板已保存，可以填写两版文案。', { exact: true }).waitFor()
    if (await page.getByText('查看原版人物 JSON', { exact: true }).count() !== 3) throw Error('Native personas missing')
    await page.getByText('查看原版人物 JSON', { exact: true }).first().click()
    await page.getByRole('button', { name: '运行 A/B 盲测', exact: true }).click()
    await page.getByText('全部反馈已保存，可以查看配对结果。', { exact: true }).waitFor()
    await page.reload()
    await page.locator('#results').waitFor({ state: 'visible' })
    const comparison = await (await page.request.get(backend + '/api/jury/comparisons/' + new URL(page.url()).searchParams.get('comparison'))).json()
    if (comparison.next_index !== null || comparison.exposures.length !== 6 || comparison.pairs.length !== 3) throw Error('Incomplete A/B results')
    await page.screenshot({ path: path.join(out, 'completed.png'), fullPage: true })
    await page.setViewportSize({ width: 390, height: 844 })
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw Error('Consumer page overflows on mobile')
    if (errors.length) throw Error(errors.join('\n'))
    console.log('Native personas, marketing theory, parallel A/B, saved results, refresh and mobile consumer page passed.')
  } finally { await browser.close() }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
