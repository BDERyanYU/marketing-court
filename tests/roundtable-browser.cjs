const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('../frontend/node_modules/@playwright/test')

async function main() {
  const url = process.env.APP_URL || 'http://127.0.0.1:5173'
  const output = process.env.BROWSER_OUTPUT_DIR || 'test-results/roundtable'
  const browser = await chromium.launch({ executablePath: process.env.BROWSER_PATH, headless: true })
  const page = await browser.newPage({ viewport: { width: 1536, height: 920 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  try {
    await page.goto(url + '/review')
    await page.getByRole('button', { name: '打开预设案例' }).click()
    await page.getByRole('button', { name: '圆桌复核', exact: true }).first().click()
    const dialog = page.getByRole('dialog', { name: '圆桌复核' })
    await dialog.getByLabel('你想核对的问题').fill('现有证据能否支持 100% Eco-Friendly 宣称？')
    let allowStart
    const release = new Promise((resolve) => { allowStart = resolve })
    await page.route('**/api/reviews/*/risks/*/discussions', async (route) => {
      await release
      await route.continue()
    })
    try {
      await dialog.getByRole('button', { name: '启动圆桌讨论' }).click()
      await dialog.getByText('正在组建圆桌').waitFor()
      assert.equal(await dialog.getByRole('button', { name: '返回审核' }).isEnabled(), false)
      await page.keyboard.press('Escape')
      assert.equal(await dialog.isVisible(), true)
    } finally {
      allowStart()
    }
    await dialog.locator('[data-meeting-status="finished"]').waitFor()
    await dialog.getByRole('img', { name: '木质圆桌' }).waitFor()
    assert.equal(await dialog.locator('[data-seat-id]').count(), 4)
    assert.equal(await dialog.locator('.rt-round-heading').count(), 3)
    const firstRound = dialog.getByRole('button', { name: '第 1 轮 · 初步解读' })
    if (await firstRound.getAttribute('aria-expanded') === 'false') await firstRound.click()
    await dialog.locator('[data-turn-index="2"]').click()
    const bubble = dialog.locator('[data-speaking-for]')
    assert.equal(await bubble.count(), 1)
    const speakerId = await bubble.getAttribute('data-speaking-for')
    assert.equal(await dialog.locator('[data-spotlight-for]').getAttribute('data-spotlight-for'), speakerId)
    const light = await dialog.locator('[data-spotlight-for]').boundingBox()
    const speakerSeat = await dialog.locator(`[data-seat-id="${speakerId}"]`).boundingBox()
    assert.ok(Math.abs((light.x + light.width / 2) - (speakerSeat.x + speakerSeat.width / 2)) < 2)

    const other = dialog.locator(`[data-seat-id]:not([data-seat-id="${speakerId}"])`).first()
    const beforeHover = await other.boundingBox()
    await other.hover()
    await dialog.locator('.rt-persona').waitFor()
    assert.deepEqual(await other.boundingBox(), beforeHover, 'hover must not move the seat')
    assert.equal(await bubble.getAttribute('data-speaking-for'), speakerId)
    fs.mkdirSync(output, { recursive: true })
    await page.waitForFunction(() => Number(getComputedStyle(document.querySelector('.rt-light')).opacity) >= 0.99)
    await page.screenshot({ path: path.join(output, 'roundtable-desktop.png') })
    await page.mouse.move(10, 10)
    await dialog.getByRole('button', { name: '下一条发言' }).click()
    assert.equal(await bubble.count(), 1)
    assert.notEqual(await bubble.getAttribute('data-speaking-for'), speakerId)
    await dialog.getByText('主持纪要', { exact: true }).click()
    await dialog.getByText('演示纪要', { exact: false }).last().waitFor()
    await page.setViewportSize({ width: 1040, height: 460 })
    const landscapeBubble = await bubble.boundingBox()
    const landscapeStage = await dialog.locator('.rt-stage').boundingBox()
    assert.ok(landscapeBubble.y >= landscapeStage.y, 'speech should fit above the portrait in short viewports')
    await page.setViewportSize({ width: 390, height: 844 })
    assert.equal(await dialog.evaluate((el) => el.scrollWidth > el.clientWidth), false)
    const mobileBubble = await bubble.boundingBox()
    assert.ok(mobileBubble.x >= 0 && mobileBubble.x + mobileBubble.width <= 390)

    await page.screenshot({ path: path.join(output, 'roundtable-mobile.png') })
    await dialog.getByRole('button', { name: '返回审核' }).click()
    await dialog.waitFor({ state: 'hidden' })
    await page.getByRole('heading', { name: '每项风险，都能追溯。' }).waitFor()
    await page.getByRole('button', { name: '圆桌复核', exact: true }).first().click()
    await dialog.locator('[data-meeting-status="finished"]').waitFor()
    assert.equal(await dialog.locator('[data-seat-id]').count(), 4)
    assert.deepEqual(errors, [])
    console.log('Roundtable browser flow passed: risk launch, native participants, stable seating and hover, spotlight, one speech bubble, rounds, memo, mobile and reopen.')
  } finally {
    await browser.close()
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
