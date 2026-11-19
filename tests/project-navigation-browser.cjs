const { chromium } = require("../frontend/node_modules/@playwright/test");
const fs = require("node:fs");
async function main() {
  const app = process.env.APP_URL || "http://127.0.0.1:5180";
  const browser = await chromium.launch({
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1703, height: 955 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    const fixture = await (await page.request.post(app + "/api/demo")).json();
    const projects = await (
      await page.request.get(app + "/api/projects")
    ).json();
    const project = projects.find((p) => p.project_id === fixture.project_id);
    await page.goto(app + "/review");
    await page.locator(".sidebar-project").first().waitFor();
    if (
      await page
        .getByRole("button", { name: "审核工作台", exact: true })
        .count()
    )
      throw Error("Old navigation remains");
    if (
      await page
        .getByText("当前范围：英国环保文字宣称", { exact: true })
        .count()
    )
      throw Error("Removed note remains");
    if ((await page.locator(".sidebar-project").count()) !== projects.length)
      throw Error("Not all projects listed");
    await page
      .locator(".sidebar-project")
      .filter({ hasText: project.name })
      .click();
    await page
      .getByRole("heading", { name: project.name, exact: true })
      .waitFor();
    await page
      .locator(".project-history .history-list > button")
      .first()
      .waitFor();
    await page
      .locator(".project-history .history-list > button")
      .first()
      .click();
    await page.getByRole("heading", { name: "每项风险，都能追溯。" }).waitFor();
    await page.reload();
    await page.getByRole("heading", { name: "每项风险，都能追溯。" }).waitFor();
    const other = projects.find((p) => p.project_id !== project.project_id);
    if (other) {
      await page
        .locator(".sidebar-project")
        .filter({ hasText: other.name })
        .first()
        .click();
      await page
        .getByRole("heading", { name: other.name, exact: true })
        .waitFor();
      await page.reload();
      await page
        .getByRole("heading", { name: other.name, exact: true })
        .waitFor();
      await page
        .getByRole("button", { name: "添加素材审核", exact: true })
        .first()
        .click();
      if (
        (await page.getByLabel("所属项目", { exact: true }).inputValue()) !==
        other.project_id
      )
        throw Error("Add material lost selected project");
    }
    await page.getByRole("button", { name: "项目与素材", exact: true }).click();
    await page.reload();
    await page
      .getByRole("heading", { name: "让每一句宣称，都有据可循。" })
      .waitFor();
    if (
      (await page.getByLabel("所属项目", { exact: true }).inputValue()) !== ""
    )
      throw Error("Home not restored");
    for (const width of [320, 390, 740, 890, 1703]) {
      await page.setViewportSize({ width, height: 955 });
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        )
      )
        throw Error("Overflow at " + width);
      const list = page.locator(".sidebar-project-list");
      await list.evaluate((e) => {
        e.scrollTop = e.scrollHeight;
        e.scrollLeft = e.scrollWidth;
      });
      await page.locator(".sidebar-project").last().click();
      await page.locator(".project-history").waitFor();
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        )
      )
        throw Error("Project overflow at " + width);
      fs.mkdirSync("test-results/project-navigation", { recursive: true });
      if (width === 390 || width === 1703)
        await page.screenshot({
          path: `test-results/project-navigation/project-${width}.png`,
          fullPage: true,
        });
    }
    if (errors.length) throw Error(errors.join("\n"));
    console.log(
      "Project list, report opening, selected-project upload, refresh across projects/home and five screen widths passed.",
    );
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
