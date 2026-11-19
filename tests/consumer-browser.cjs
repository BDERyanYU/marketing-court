const { chromium } = require("../frontend/node_modules/@playwright/test");
const path = require("node:path");
const fs = require("node:fs");
async function main() {
  const app = process.env.APP_URL || "http://127.0.0.1:5180";
  const backend = process.env.API_PROXY_URL || "http://127.0.0.1:8021";
  const out = path.resolve("test-results/consumer-browser");
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const errors = [];
  let disconnectOnce = true;
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/jury/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/advance-members") && disconnectOnce) {
      disconnectOnce = false;
      const saved = await route.fetch({ url: backend + url.pathname });
      if (!saved.ok()) throw Error("Could not save partial feedback");
      return route.fulfill({
        status: 502,
        json: { detail: "测试连接中断，请继续测试。" },
      });
    }
    await route.fulfill({
      response: await route.fetch({ url: backend + url.pathname + url.search }),
    });
  });
  try {
    const health = await (
      await page.request.get(backend + "/api/jury/demo")
    ).json();
    if (health.mode !== "demo") throw Error("Use an isolated demo server");
    await page.goto(app + "/jury");
    await page
      .getByRole("heading", { name: "数字人像测试", exact: true })
      .waitFor();
    const nav = page.getByRole("navigation", { name: "主导航" });
    const navStyles = await nav
      .locator(":scope > button")
      .evaluateAll((buttons) =>
        buttons.map((button) => ({
          padding: getComputedStyle(button).padding,
          fontSize: getComputedStyle(button).fontSize,
          borderRadius: getComputedStyle(button).borderRadius,
        })),
      );
    if (
      navStyles.length < 2 ||
      JSON.stringify(navStyles[0]) !== JSON.stringify(navStyles[1])
    )
      throw Error("Navigation styles differ");
    if (
      (await nav
        .getByRole("button", { name: "数字人像测试", exact: true })
        .getAttribute("aria-current")) !== "page"
    )
      throw Error("Missing selected navigation");
    await page.getByRole("button", { name: "用水杯样例", exact: true }).click();
    await page
      .getByRole("combobox", { name: "补充目标画像（可选）", exact: true })
      .selectOption("report");
    await page
      .getByRole("spinbutton", { name: "测试人像数", exact: true })
      .fill("3");
    await page.getByRole("button", { name: "生成人像", exact: true }).click();
    await page
      .getByText("数字人像已保存，可以填写两版文案。", { exact: true })
      .waitFor();
    if (
      (await page.getByText("查看原版人物 JSON", { exact: true }).count()) !== 3
    )
      throw Error("Native personas missing");
    await page.getByText("查看原版人物 JSON", { exact: true }).first().click();
    await page
      .getByRole("button", { name: "运行 A/B 盲测", exact: true })
      .click();
    await page
      .getByText("测试连接中断，请继续测试。", { exact: true })
      .waitFor();
    await page.reload();
    await page.getByRole("button", { name: "继续测试", exact: true }).click();
    await page
      .getByText("全部反馈已保存，可以查看配对结果。", { exact: true })
      .waitFor();
    await page.reload();
    await page.locator("#results").waitFor({ state: "visible" });
    const comparison = await (
      await page.request.get(
        backend +
          "/api/jury/comparisons/" +
          new URL(page.url()).searchParams.get("comparison"),
      )
    ).json();
    if (
      comparison.next_index !== null ||
      comparison.exposures.length !== 6 ||
      comparison.pairs.length !== 3
    )
      throw Error("Incomplete A/B results");
    await page.getByRole("button", { name: "项目与素材", exact: true }).click();
    await page
      .getByRole("heading", { name: "让每一句宣称，都有据可循。" })
      .waitFor();
    await page
      .getByRole("button", { name: "数字人像测试", exact: true })
      .click();
    await page.locator("#results").waitFor({ state: "visible" });
    await page.locator(".persona-pair summary").first().click();
    await page.screenshot({
      path: path.join(out, "completed.png"),
      fullPage: true,
    });
    for (const width of [320, 390, 740, 890, 1440]) {
      await page.setViewportSize({ width, height: 955 });
      await page.evaluate(() => {
        if (document.activeElement instanceof HTMLElement)
          document.activeElement.blur();
        window.scrollTo({ top: 0, behavior: "instant" });
      });
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        )
      )
        throw Error(`Digital persona page overflows at ${width}`);
      if ([390, 890].includes(width))
        await page.screenshot({
          path: path.join(out, `persona-${width}.png`),
          fullPage: true,
        });
    }
    if (await page.getByRole("alert").count())
      throw Error("Unexpected error banner");
    await page.getByRole("button", { name: "新建测试", exact: true }).click();
    await page.route("**/api/jury/panels/missing-record", (route) =>
      route.fulfill({ status: 404, json: { detail: "找不到该测试记录。" } }),
    );
    await page.goto(app + "/jury?panel=missing-record");
    await page.getByText("找不到该测试记录。", { exact: true }).waitFor();
    await page.getByRole("button", { name: "新建测试", exact: true }).click();
    if (await page.getByRole("alert").count())
      throw Error("Unable to reset missing record");
    await page.reload();
    await page
      .getByRole("button", { name: "用水杯样例", exact: true })
      .waitFor();
    if (errors.length) throw Error(errors.join("\n"));
    console.log(
      "Native personas, marketing theory, parallel A/B, saved results, refresh and mobile consumer page passed.",
    );
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
