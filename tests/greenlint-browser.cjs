const { chromium } = require('../frontend/node_modules/@playwright/test')
const fs = require('node:fs')
const path = require('node:path')

async function main() {
  const app = process.env.APP_URL || 'http://127.0.0.1:5173'
  const backend = process.env.API_PROXY_URL || 'http://127.0.0.1:8012'
  const output = path.resolve('test-results/greenlint-browser')
  fs.mkdirSync(output, { recursive: true })
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  const forward = async route => {
    const url = new URL(route.request().url())
    const response = await route.fetch({ url: `${backend}${url.pathname}${url.search}` })
    await route.fulfill({ response })
  }
  await page.route('**/api/**', forward)
  await page.route('**/health', forward)
  try {
    const health = await page.request.get(`${backend}/health`)
    if ((await health.json()).mode !== 'demo') throw new Error('Use an isolated demo backend')
    await page.goto(`${app}/?ui=v2`)
    await page.getByRole('heading', { name: '同一套方法，看见风险与边界' }).waitFor()
    await page.screenshot({ path: path.join(output, 'library-desktop.png'), fullPage: true })
    for (const [id, title, count] of [['apple-watch', 'Apple Watch 碳中和宣称', 1], ['eco-dog-bed', 'Eco Dog Bed 环保系列宣称', 5], ['copier-paper', 'Copier Paper 再生纸文案', 0]]) {
      await page.getByRole('button', { name: `打开${title}` }).click()
      await page.getByRole('heading', { name: '广告文案', exact: true }).waitFor()
      if (await page.locator('.risk-card').count() !== count) throw new Error(`${id} risk count mismatch`)
      if (await page.locator('.asset-canvas img').count()) throw new Error('Text example displayed a fabricated original image')
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.screenshot({ path: path.join(output, `${id}-desktop.png`), fullPage: true })
      if (count) {
        await page.locator('.text-risk').last().click()
        if (await page.locator('.risk-card.active').count() !== 1) throw new Error('Text selection did not select risk')
        await page.locator('.risk-card.active .package-rule-note summary').click()
        const rewrite = page.locator('.risk-card.active').getByRole('button', { name: '谨慎改写与复核' })
        if (await rewrite.count()) await rewrite.click()
        await page.getByRole('heading', { name: '文案改写与复核', exact: true }).waitFor()
        const closeTask = page.getByRole('button', { name: '关闭完成提示' })
        if (await closeTask.count()) await closeTask.click()
        await page.locator('.risk-card.active').getByRole('button', { name: '提出异议' }).click()
        await page.getByRole('heading', { name: '观点可以交锋，证据必须可查。' }).waitFor()
        const auto = page.getByRole('button', { name: '自动完成庭审' })
        if (await auto.count()) await auto.click()
        await page.getByRole('heading', { name: '证据不足，建议补证' }).waitFor()
        if (await page.locator('.turn').count() !== 4) throw new Error('Court did not complete four turns')
        await page.reload()
        await page.getByRole('heading', { name: '证据不足，建议补证' }).waitFor()
        await page.getByRole('button', { name: '返回审核', exact: true }).click()
      } else {
        await page.getByRole('heading', { name: '正面对照：未发现明显风险' }).waitFor()
        if (!await page.locator('.intro').first().textContent().then(t => t.includes('欧盟'))) throw new Error('EU sample mislabeled UK')
        await page.getByText('“darker than conventional” 比较的是纸张颜色，没有被误判为环保性能比较。').waitFor()
        await page.reload()
        await page.getByRole('heading', { name: '正面对照：未发现明显风险' }).waitFor()
      }
      for (const width of [320, 390, 890, 1440]) {
        await page.setViewportSize({ width, height: 1000 })
        if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`${id} overflows at ${width}`)
        if (width === 390) await page.screenshot({ path: path.join(output, `${id}-mobile.png`), fullPage: true })
      }
      const download = page.waitForEvent('download')
      await page.getByRole('link', { name: '导出 JSON 报告' }).click()
      const file = path.join(output, `${id}.json`)
      const downloaded = await download
      console.log(id, 'download', downloaded.suggestedFilename())
      await downloaded.saveAs(file)
      const report = JSON.parse(fs.readFileSync(file))
      if (report.review.example.case_id !== id || report.review.risks.length !== count) throw new Error('Export is from the wrong example')
      await page.getByRole('button', { name: '项目与素材', exact: true }).click()
    }
    await page.setViewportSize({ width: 390, height: 844 })
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.screenshot({ path: path.join(output, 'library-mobile.png'), fullPage: true })
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Library overflows on mobile')
    if (errors.length) throw new Error(errors.join('\n'))
    console.log('GreenLint browser passed: three cases, exact counts, markets, text selection, rules, rewrite, court, restore, reports, desktop/mobile.')
  } finally { await browser.close() }
}
main().catch(e => { console.error(e); process.exitCode = 1 })
