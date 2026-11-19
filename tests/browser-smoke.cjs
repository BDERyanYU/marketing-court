/* Uses the installed browser and Playwright package supplied through environment. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '../frontend/node_modules/@playwright/test')
const fs = require('node:fs')
const path = require('node:path')

async function main() {
  process.chdir(path.resolve(__dirname, '..'))
  const appUrl = process.env.APP_URL || 'http://127.0.0.1:5173'
  const backendUrl = process.env.API_PROXY_URL
  const output = process.env.BROWSER_OUTPUT_DIR || 'test-results'
  fs.mkdirSync(output, { recursive: true })
  const browser = await chromium.launch({ executablePath: process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  if (backendUrl) {
    const forward = async route => {
      const original = new URL(route.request().url())
      const response = await route.fetch({ url: `${backendUrl}${original.pathname}${original.search}` })
      await route.fulfill({ response })
    }
    await page.route('**/api/**', forward)
    await page.route('**/health', forward)
    await page.route('**/jury', forward)
  }
  async function checkLayout(label) {
    for (const width of [320, 390, 600, 740, 890, 1100, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`${label} layout overflows at ${width}px`)
      if (width === 390 || width === 890) await page.screenshot({ path: path.join(output, `${label}-${width}.png`), fullPage: true })
    }
  }
  try {
    const health = await page.request.get(`${backendUrl || appUrl}/health`)
    if (!health.ok() || (await health.json()).mode !== 'demo') throw new Error('Browser smoke requires a demo backend; use API_PROXY_URL to target an isolated demo server.')
    await page.goto(appUrl)
    await page.getByRole('button', { name: '打开预设案例' }).waitFor()
    for (const name of ['目标市场', '商品类别']) {
      const select = page.getByRole('combobox', { name, exact: true })
      if (!await select.isEnabled()) throw new Error(`${name} selector is disabled`)
      await select.focus()
      await page.keyboard.press('ArrowDown')
      await page.keyboard.press('Enter')
    }
    await page.screenshot({ path: path.join(output, 'setup-desktop.png'), fullPage: true })
    await page.getByLabel('选择广告图片').setInputFiles('examples/eco-bottle.png')
    await page.locator('.upload-preview').evaluate(img => img.decode())
    await page.screenshot({ path: path.join(output, 'upload-preview.png'), fullPage: true })
    await page.reload()
    await page.getByRole('button', { name: '打开预设案例' }).waitFor()
    await checkLayout('setup')
    await page.getByRole('button', { name: '打开预设案例' }).click()
    await page.getByRole('heading', { name: '每项风险，都能追溯。' }).waitFor()
    await page.getByRole('button', { name: '查看风险：100% Eco-Friendly' }).waitFor()
    await page.locator('.asset-canvas img').evaluate(img => img.decode())
    if (!await page.locator('.asset-canvas img').evaluate(img => img.naturalWidth === 1000)) throw new Error('Asset image did not load')
    await page.screenshot({ path: path.join(output, 'review-desktop.png'), fullPage: true })
    const rewrite = page.getByRole('button', { name: '谨慎改写与复核' })
    if (await rewrite.count()) await rewrite.click()
    await page.getByRole('heading', { name: '文案改写与复核', exact: true }).waitFor()
    await checkLayout('review')
    const freshCase = await page.request.post(`${backendUrl || appUrl}/api/risks/demo-eco-bottle/appeals`)
    if (!freshCase.ok()) throw new Error('Could not create a fresh rehearsal case')
    await page.getByRole('button', { name: '提出异议' }).click()
    await page.getByRole('heading', { name: '观点可以交锋，证据必须可查。' }).waitFor()
    const advance = page.getByRole('button', { name: '推进下一步' })
    if (await advance.count()) {
      await advance.click()
      await page.getByText('第一轮 · 辩方', { exact: false }).waitFor()
      await page.reload()
      await page.getByText('第一轮 · 辩方', { exact: false }).waitFor()
      await page.getByRole('button', { name: '自动完成庭审' }).click()
    }
    await page.getByRole('heading', { name: '证据不足，建议补证' }).waitFor({ timeout: 30000 })
    await page.screenshot({ path: path.join(output, 'court-desktop.png'), fullPage: true })
    await page.reload()
    await page.getByRole('heading', { name: '证据不足，建议补证' }).waitFor()
    await checkLayout('court')
    await page.getByRole('button', { name: '返回审核' }).click()
    await page.getByRole('heading', { name: '每项风险，都能追溯。' }).waitFor()
    const download = page.waitForEvent('download')
    await page.getByRole('link', { name: '导出 JSON 报告' }).click()
    await (await download).saveAs(path.resolve(output, 'report.json'))
    const report = JSON.parse(fs.readFileSync(path.join(output, 'report.json'), 'utf8'))
    if (!report.court_cases.some(c => c.status === 'completed') || !report.rewrites.length) throw new Error('Incomplete exported report')
    await page.getByRole('link', { name: '消费者模拟（独立页面）' }).click()
    await page.waitForURL('**/jury')
    if (!(await page.content()).includes('水杯样例')) throw new Error('Existing consumer simulator page is unavailable')
    await page.goto(`${appUrl}/?ui=v1`)
    await page.getByRole('button', { name: '打开预设案例' }).waitFor()
    await page.screenshot({ path: path.join(output, 'v1-desktop.png'), fullPage: true })
    const originalBackground = await page.locator('.sidebar').evaluate(el => getComputedStyle(el).backgroundColor)
    if (!await page.getByRole('combobox', { name: '目标市场', exact: true }).isEnabled()) throw new Error('Preserved v1 market selector is disabled')
    await page.getByRole('button', { name: '打开预设案例' }).click()
    await page.getByRole('heading', { name: '每项风险，都能追溯。' }).waitFor()
    await page.goto(appUrl)
    await page.getByRole('heading', { name: '每项风险，都能追溯。' }).waitFor()
    if (await page.locator('.sidebar').evaluate(el => getComputedStyle(el).backgroundColor) === originalBackground) throw new Error('Original and redesigned styles are not isolated')
    const uploadPage = await browser.newPage()
    uploadPage.on('pageerror', e => errors.push(e.message))
    let projectInput
    let uploaded = false
    await uploadPage.route('**/health', route => route.fulfill({ json: { status: 'ok', mode: 'live', model: 'preview-test' } }))
    await uploadPage.route('**/api/**', async route => {
      const request = route.request()
      const endpoint = new URL(request.url()).pathname
      if (endpoint === '/api/demo-cases') return route.fulfill({ json: [] })
      if (endpoint === '/api/projects') {
        if (request.method() === 'GET') return route.fulfill({ json: [] })
        projectInput = request.postDataJSON()
        return route.fulfill({ status: 201, json: { project_id: 'upload-test-project', ...projectInput } })
      }
      if (endpoint === '/api/projects/upload-test-project/assets') {
        uploaded = (request.headers()['content-type'] || '').includes('multipart/form-data') && request.postDataBuffer().includes(Buffer.from('eco-bottle.png'))
        return route.fulfill({ status: 201, json: { asset_version_id: 'upload-test-asset', project_id: 'upload-test-project', image_url: '/examples/eco-bottle.png', kind: 'image', original_filename: 'eco-bottle.png', width: 1000, height: 1200 } })
      }
      if (endpoint === '/api/assets/upload-test-asset/reviews') return route.fulfill({ status: 202, json: { task_id: 'upload-test-task', resource_id: 'upload-test-asset', kind: 'review', status: 'running', stage: 'asset_parsing' } })
      if (endpoint === '/api/tasks/upload-test-task') return route.fulfill({ json: { task_id: 'upload-test-task', resource_id: 'upload-test-asset', kind: 'review', status: 'interrupted', stage: 'asset_parsing', error: '界面验证任务，可以重试。' } })
      throw new Error(`Unexpected upload request: ${endpoint}`)
    })
    await uploadPage.route('**/examples/eco-bottle.png', route => route.fulfill({ path: path.resolve('examples/eco-bottle.png') }))
    await uploadPage.goto(appUrl)
    await uploadPage.getByLabel('项目名称', { exact: true }).fill('新版上传验证')
    await uploadPage.getByLabel('选择广告图片').setInputFiles('examples/eco-bottle.png')
    await uploadPage.getByRole('button', { name: '上传并开始审核' }).click()
    await uploadPage.getByRole('heading', { name: '每项风险，都能追溯。' }).waitFor()
    await uploadPage.getByRole('button', { name: '重试此任务' }).waitFor()
    if (!uploaded || projectInput?.name !== '新版上传验证' || projectInput.market !== 'GB' || projectInput.product_category !== 'reusable_bottle') throw new Error('Selected project context or image upload was lost')
    if (await uploadPage.getByRole('button', { name: '关闭错误提示' }).count()) throw new Error('Upload produced an unexpected error')
    await uploadPage.close()
    if (errors.length) throw new Error(errors.join('\n'))
    console.log('Browser flow passed: selectors, image preview, upload payload, retry state, fixture, overlay, rewrite, court, refresh, 7 screen widths, JSON export, existing jury page, preserved v1 and isolated styles.')
  } finally { await browser.close() }
}
main().catch(e => { console.error(e); process.exitCode = 1 })
