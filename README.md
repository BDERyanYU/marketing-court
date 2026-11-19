# AI Marketing Court

面向英国环保广告文字宣称的本机演示应用：提交广告图片、文案或二者 → OCR 与文字提取 → 有来源的风险审核 → 谨慎改写与一次复核 → 两轮控辩 → 独立法官复核。

目前已实现同一项目多次提交、图片/文案/联合审核、PaddleOCR 坐标提取、DeepSeek 文字审核、有限 CMA 规则检索、文案版本、模拟法庭、进度恢复和 JSON 报告。图像语义理解、广告 PDF/DOCX 审核和多人在线部署尚未实现。

已保留远端新增的消费者文案模拟，可从前端侧栏进入独立页面 `/jury`：报告画像提取、情境面板和配对文案比较沿用其现有实现与测试，尚未与广告审核版本自动对接。详见 [消费者模拟](docs/consumer-jury.md)。

界面第二版采用深蓝导航、浅色证据工作台和控辩时间线。第一版源码保存在 `frontend/src/v1/`，可通过 [第一版预览](http://127.0.0.1:5173/?ui=v1) 打开；新版侧栏与手机页脚也提供入口。Git 标签 `ui-v1` 保留改版前完整代码。设计与版本说明见 [界面设计](docs/interface-design.md)。

首页新增 GreenLint v1.2 的两个负面文案案例（英国 Apple Watch、Eco Dog Bed）和一个正面案例（欧盟 Copier Paper），展示包内规则的 1 / 5 / 0 项风险结果。支持文案选择、规则说明、改写复核、庭审与报告导出；原水杯案例保留。案例数据为预设演示，不扩大实时审核覆盖范围，详见 [案例来源与边界](docs/greenlint-cases.md)。

## 项目与素材

每次提交可选“广告图片”“广告文案”或“图片＋文案”，也可选择已有项目添加审核版本。图片仅做文字识别，不含图像语义理解。联合审核会保留原图、输入文案与 OCR 文字；文案中的风险可单独点击，无法匹配原图时不生成坐标。改写保留原始版本，只删除选中风险的一次出现，并复核完整剩余文案。

目标市场提供英国、欧盟、美国、加拿大、澳大利亚、中国大陆、日本、韩国和新加坡；商品类别提供水杯、家居日用、电子家电、服装配饰、美妆个护、食品饮料、宠物、办公纸品、包装与其他消费品。实时规则仍为英国 CMA 通用环保宣称指引摘录，各品类专项规定未接入。其他市场仅保存素材、提取文字与宣称，结果明确标为“未作风险判定”，不借用英国规则。

`POST /api/projects/{id}/assets` 接受表单中的可选 `file` 与可选 `text`（最多 8000 字符），至少一项非空；图片和文案合并识别文字超过 8000 字符时保留素材并提示裁剪重试。原始文案也可使用既有审核启动、改写、庭审和导出接口。

首页四个预设案例统一展示于表单下方，水杯为负面案例，共三个负面案例与一个正面对照。第一版保留。

## 启动固定案例演示

需要 Python 3.12+、[uv](https://docs.astral.sh/uv/)、Node.js 20+ 与 pnpm。在仓库根目录运行：

```powershell
uv sync --locked
Copy-Item .env.example .env
uv run --no-sync --env-file .env uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

另开终端启动前端：

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

打开 [本地应用](http://127.0.0.1:5173/)，点击“打开预设案例”。默认无需 API Key，案例文字、坐标、审核结论和庭审发言均来自明确标注的固定数据。固定模式不接受新素材的实时审核。

Windows 也可运行 `scripts/start-backend.ps1` 与 `scripts/start-frontend.ps1`。脚本在当前终端运行，方便直接查看状态；首次先安装依赖。

## 启用真实 OCR 与模型

```powershell
uv sync --locked --extra ocr
```

在本机 `.env` 设置：

```dotenv
COURT_MODE=live
COURT_DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_API_KEY=你的密钥
```

模型名沿用导入庭审模块的默认值，实际可用 ID 以你的账号为准，可通过 `COURT_DEEPSEEK_MODEL` 更换。也可设置 `DEEPSEEK_API_KEY_FILE`，从本机文件读取密钥。不要把真实密钥提交到 Git。

兼容远端的 `MARKETING_COURT_MODE` 与 `MARKETING_COURT_DEEPSEEK_MODEL` 统一配置；如设置，会覆盖审核、庭审与消费者模块的单独模式和模型。`JURY_MODE` 默认使用固定数据。原有 `python -m marketing_court` 启动入口仍可使用。

重启后端后上传 `examples/eco-bottle.png`，即可运行真实图片链路。实时模式也能打开预设审核案例并生成真实庭审；预设审核结果仍会标注来源，其改写复核需要切回固定模式或重新实时审核图片。

PaddleOCR 首次运行会下载识别模型，应在演示前预热：

```powershell
.venv/Scripts/python.exe scripts/warmup-ocr.py
```

模型在 `data/paddle-cache`，数据库默认在 `data/marketing_court.sqlite3`，上传文件在 `data/uploads`，均不进 Git。Windows 使用普通终端运行即可；如 OCR 下载失败，检查网络及缓存目录写权限。已禁用存在 Windows 兼容问题的 MKL-DNN 推理选项。

## 测试与真实演练

```powershell
.venv/Scripts/python.exe -m pytest -q
cd frontend
pnpm build
```

后端测试使用隔离数据库与可控模型，不产生供应商费用。前端依赖包含 Playwright，浏览器脚本默认使用本机 Chrome，可用 `BROWSER_PATH` 指定其他 Chromium 浏览器。前后端启动后，在 `frontend` 运行 `pnpm test:browser`。运行 `pnpm format` 可统一前端格式。

真实模式后端启动后，运行以下命令，会将示例文字发送至模型并产生 API 费用：

```powershell
.venv/Scripts/python.exe scripts/live-smoke.py
```

演练会上传示例图、检查风险定位、运行一次改写复核、完成庭审，并将报告保存到本地 `test-results/live-report.json`。完整供应商验证需要配置有效密钥；脚本不会自动切换到固定模式。

## 模块与接口

- 前端：项目与素材、审核工作台、模拟法庭。
- 后端：`api` 路由，`models` 共享契约，`core` 配置与存储，`services` OCR/规则/改写，`workflows` 审核编排，`court` 庭审状态与角色。
- 共享关系：Project → AssetVersion → Review → Claim / RiskItem → CourtCase → DebateTurn / Judgment。
- 审核任务每秒轮询真实状态；OCR、宣称提取与风险结果可保存检查点。重启后中断任务可重试，已完成结果保留。
- 庭审采用单进程、逐步推进；失败步骤可重试。已保存步骤重复请求不再调用模型，但进程在供应商返回后、写入数据库前退出仍可能导致重试调用。
- 上传、任务与庭审 API 见 [本地接口文档](http://127.0.0.1:8000/docs)。项目、资产、审核和庭审均持久化；浏览器记住当前记录。

## 产品边界

仅支持 PNG/JPG、英国普通消费品环保文字宣称和未提供产品证明的案例。CMA 规则包是已核对原文的监管指引摘录，不是完整法律库。未识别到本主题风险不表示广告已获准投放。

改写采用删除选中待补证宣称的保守策略，保留其余原文，不新增产品事实；仅生成文案版本，不修改原图。审核、复核和裁判结果分别保存。

实时 OCR 在本机执行，提取文字和案卷规则发送至 DeepSeek；本地保存原图、文字与结果，不记录密钥。此版本按本机单人使用设计，只绑定 `127.0.0.1`，未实现登录和项目访问权限。

详见 [原始产品说明](AI%20Marketing%20Court%20V1.0.md)、[架构](docs/architecture.md)、[演示脚本](docs/demo-script.md) 和 [验证记录](docs/validation.md)。AI 辅助审核与非正式风险复核不构成法律意见或投放批准。
