# AI Marketing Court

当前版本：**V2.2**（欢迎页与跨平台一键启动）。上一已标记版本 [`ui-v2.1`](https://github.com/BDERyanYU/marketing-court/tree/ui-v2.1) 保留。版本说明见 [更新记录](CHANGELOG.md)。

当前整合版默认采用**第二版素材审核界面**，合入朋友分支的 TinyTroupe 原生画像派生、营销理论文件和消费者 A/B 并行评价。模拟法庭功能已移除。第三版圆桌工作区保留在 `?ui=v3`，第一版审核布局保留在 `?ui=v1`。

完整能力：同一项目图片/文案/联合审核、PaddleOCR 文字坐标、DeepSeek 风险审核、英国 CMA 有限环保规则、改写与一次复核、独立版本、进度恢复、JSON 导出，以及调研报告驱动的消费者模拟。其他市场未接入规则时仅提取文字和宣称。

## 本机启动

### 给朋友的一键启动（Windows / macOS）

无需预装 Git、Python 或 Node.js。首次联网运行下面对应的一行命令，自动下载项目、安装组件并打开网页；首次按提示粘贴 DeepSeek 密钥即可，输入时不显示。后续双击桌面的 **Marketing Court**。关闭启动窗口即停止本机服务，项目和密钥留在该电脑，不写进 GitHub。

Windows：打开 **PowerShell**，粘贴后回车：

```powershell
irm https://raw.githubusercontent.com/BDERyanYU/marketing-court/main/scripts/install-windows.ps1 | iex
```

macOS：打开 **终端**，粘贴后回车：

```bash
curl -fsSL https://raw.githubusercontent.com/BDERyanYU/marketing-court/main/scripts/install-macos.sh | /bin/bash
```

已下载项目的用户也可双击根目录的 `Start-Windows.cmd` 或 `Start-Mac.command`。Mac 如提示无执行权限，在终端执行 `bash Start-Mac.command`；下载安装入口会自动设置桌面快捷方式。

审核和数字人像测试统一使用 `deepseek-flash`，启动前检查密钥和模型是否可用。首次运行会安装并验证 OCR，可能耗时较长；默认使用 PaddleOCR，Intel Mac（macOS 13+）以及 Windows 中文等非 ASCII 安装路径使用兼容的 ONNX OCR。这里只是本机运行，不会发布公网网站，也不会将模型密钥放到网页中。安装位置、重试与更新见 [一键启动说明](docs/one-click-start.md)。

### 手动开发启动

审核报告的风险卡提供 **圆桌复核**。Moot 使用独立会议库和既有模型配置。手动为已有环境启用圆桌可运行 `uv sync --locked --inexact --extra roundtable`。

在「数字人像测试」生成并保存人像后，可在发起圆桌时从下拉框邀请一位。圆桌保留这位人像的原始设定，分配独立座位和抽象角色插画，发言记录随会议保存。悬停或点击座位可以看人设。数字人像提供模拟消费视角，原画像和 A/B 结果留在各自的记录中。

需要 Python 3.12+、uv 和 Node.js 20+。

```powershell
uv sync --locked --extra ocr --extra roundtable
Copy-Item .env.example .env
.venv/Scripts/python.exe -m uvicorn backend.app.main:create_app --factory --env-file .env --host 127.0.0.1 --port 8000 --workers 1
```

已有 `.env` 时保留原文件。另开终端：

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

打开 [欢迎页](http://127.0.0.1:5173/)，点击 **Open the court** 进入原有[项目主页面](http://127.0.0.1:5173/review)。[数字人像测试](http://127.0.0.1:5173/jury)仍与项目主页面共用侧栏和工作区样式，`?ui=v1`、`?ui=v2`、`?ui=v3` 入口保留。Windows 启动脚本位于 `scripts/`。审核固定模式支持四个预设案例，数字人像测试提供水杯与复印纸样例；固定模式不能审核任意新素材。

欢迎页使用独立 HTML，展示用户提供的六类广告图片：家庭暴力公益、社会伦理、视觉冲击、宗教争议、伦理争议和性暗示。图片按原比例完整展示，保留深灰色扫描线与粒子、双向拖动和暂停功能。图片保存在 `frontend/public/landing-ads/`，来源记录见同目录 `sources.json`；字体已嵌入，授权文件位于 `frontend/public/font-licenses/`，欢迎页无需外部图片服务。扫描左侧为对应主题的讨论提示，顶部指示当前示例，不调用审核接口，也不代表真实审核结果。

## 实时模型与画像

本机 `.env` 的 `COURT_MODE=live` 控制审核，`JURY_MODE=live` 控制消费者模拟；为兼容已有设置保留这些变量名。两者共用 `DEEPSEEK_API_KEY` 或 `DEEPSEEK_API_KEY_FILE`，默认模型是 `deepseek-flash`。`MARKETING_COURT_MODE` 和 `MARKETING_COURT_DEEPSEEK_MODEL` 可覆盖两者。

消费者模拟默认每批并行评价两位角色，通过 `JURY_MAX_CONCURRENT_MEMBERS` 设置。`JURY_THEORY_SKILL_FILE` 可指向仓库中的 `skills/persona-derivation/SKILL.md`；设置后重启服务生效。TinyTroupe 源码固定于 `vendor/tinytroupe`，MIT 许可证保留；Windows 提示编码和生成结果需通过实际演练验证。

DeepSeek 连接中断、超时、限流和临时服务故障最多尝试三次。密钥、余额和参数错误直接提示。审核与 A/B 结果逐步保存，刷新和重启后可以恢复。上游已接收但未返回的请求仍可能在重试时再次计费。

## 数据与验证

SQLite 默认在 `data/marketing_court.sqlite3`，消费者模拟使用独立数据库，上传文件和 Paddle 模型均在本机；密钥、数据库和运行环境不提交代码仓库。V2.1 已经用户验收并合并到 `main`；预览工作区仍使用独立数据副本。

```powershell
.venv/Scripts/python.exe -m pytest -q
cd frontend
pnpm build
```

浏览器测试和真实模型演练见 [整合验收说明](docs/v2-integration.md)。更多内容见 [架构](docs/architecture.md)、[消费者模拟](docs/consumer-jury.md)、[案例边界](docs/greenlint-cases.md)。历史产品说明保留作参考，当前范围以本说明为准。

AI 辅助审核与消费者模拟不构成法律意见、真实消费者调研或投放批准。
