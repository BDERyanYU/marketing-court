// Opt-in: submits the local English example to the configured live model.
// Run against a local server with a separate rehearsal database when possible.
const { chromium } = require('../frontend/node_modules/@playwright/test')
const path = require('node:path')
const fs = require('node:fs')

async function main() {
  const app = process.env.APP_URL || 'http://127.0.0.1:5173'
  const out = path.resolve('test-results/review-live-browser')
  fs.mkdirSync(out, { recursive: true })
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
  })
  const page = await browser.newPage({ viewport: { width: 1703, height: 1000 }, acceptDownloads: true })
  page.setDefaultTimeout(30000)
  const errors = [], results = []
  page.on('pageerror', e => errors.push(e.message))
  const checked = async response => {
    if (!response.ok()) throw Error(`API returned ${response.status()}`)
    return response.json()
  }
  const runMaterial = async (mode, create = false) => {
    await page.getByRole('button', { name: create ? '＋ 创建项目' : '添加版本', exact: true }).click()
    const dialog = page.getByRole('dialog')
    if (create) await dialog.getByLabel('项目名称', { exact: true }).fill(`审核流程自检 ${Date.now()}`)
    await dialog.getByRole('radio', { name: mode, exact: true }).check()
    if (mode !== '广告文案')
      await dialog.getByLabel('选择广告图片', { exact: true }).setInputFiles('examples/eco-bottle.png')
    if (mode !== '广告图片')
      await dialog.getByRole('textbox', { name: '广告文案', exact: true }).fill('100% Eco-Friendly. Meet the Everyday Bottle.')
    const started = page.waitForResponse(r => /\/api\/assets\/[^/]+\/reviews$/.test(r.url()) && r.request().method() === 'POST')
    await dialog.getByRole('button', { name: '保存并开始审核', exact: true }).click()
    const task = await checked(await started)
    // Refresh while the request is running: restore must follow the same task.
    await page.reload()
    await page.waitForFunction(() => {
      const banner = document.querySelector('.task-banner')
      return banner && (banner.textContent.includes('处理完成') || banner.classList.contains('failed'))
    }, null, { timeout: 330000 })
    const done = await checked(await page.request.get(`${app}/api/tasks/${task.task_id}`))
    if (done.status !== 'completed') throw Error(`${mode}: ${done.error}`)
    await page.locator('.issue').first().waitFor()
    const review = await checked(await page.request.get(`${app}/api/reviews/${done.result_id}`))
    if (review.mode !== 'live' || review.model !== 'deepseek-flash' || !review.risks.length)
      throw Error(`${mode}: expected a live risk report`)
    if (mode !== '广告文案' && (!review.anchors.length || !review.risks.some(r => r.location_status === 'located')))
      throw Error(`${mode}: missing OCR coordinates`)
    if (mode === '广告文案' && review.anchors.length) throw Error('Text review invoked image OCR')
    if (mode === '图片＋文案' && (!review.image_text || !review.supplied_text))
      throw Error('Combined review lost one input')
    const report = await checked(await page.request.get(`${app}/api/reviews/${done.result_id}/report`))
    if (report.review.review_id !== done.result_id) throw Error('Report export has wrong review')
    results.push({ mode, task_id: task.task_id, review_id: done.result_id, risks: review.risks.length, anchors: review.anchors.length })
    console.log(`${mode}: upload, refresh recovery, real review, risk report and JSON export passed.`)
  }
  try {
    await page.goto(app + '/review')
    await runMaterial('广告文案', true)
    await runMaterial('广告图片')
    await runMaterial('图片＋文案')
    const started = page.waitForResponse(r => r.url().endsWith('/rewrite') && r.request().method() === 'POST')
    await page.getByRole('button', { name: '谨慎改写与复核', exact: true }).first().click()
    const rewriteTask = await checked(await started)
    await page.waitForFunction(() => document.querySelector('.task-banner')?.textContent.includes('处理完成') || document.querySelector('.task-banner.failed'), null, { timeout: 330000 })
    const done = await checked(await page.request.get(`${app}/api/tasks/${rewriteTask.task_id}`))
    if (done.status !== 'completed') throw Error(`Rewrite: ${done.error}`)
    await page.reload()
    await page.getByLabel('审核版本', { exact: true }).waitFor()
    const rewrite = await checked(await page.request.get(`${app}/api/rewrites/${done.result_id}`))
    if (await page.getByLabel('审核版本', { exact: true }).inputValue() !== rewrite.review_id)
      throw Error('Refresh did not restore the completed recheck')
    if (errors.length) throw Error(errors.join('\n'))
    await page.screenshot({ path: path.join(out, 'completed.png'), fullPage: true })
    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ results, rewrite_task: done.task_id, errors }, null, 2))
    console.log('Real review browser flow passed for text, image, image+copy and one rewrite/recheck.')
  } finally {
    await browser.close()
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
