# AI Marketing Court

当前版本：**V2.1**，Git 标签 [`ui-v2.1`](https://github.com/BDERyanYU/marketing-court/tree/ui-v2.1)。版本说明见 [更新记录](CHANGELOG.md)。

当前整合版默认采用**第二版素材审核界面**，合入朋友分支的 TinyTroupe 原生画像派生、营销理论文件和消费者 A/B 并行评价。模拟法庭功能已移除。第三版圆桌工作区保留在 `?ui=v3`，第一版审核布局保留在 `?ui=v1`。

完整能力：同一项目图片/文案/联合审核、PaddleOCR 文字坐标、DeepSeek 风险审核、英国 CMA 有限环保规则、改写与一次复核、独立版本、进度恢复、JSON 导出，以及调研报告驱动的消费者模拟。其他市场未接入规则时仅提取文字和宣称。

## 本机启动

需要 Python 3.12+、uv 和 Node.js 20+。

```powershell
uv sync --locked --extra ocr
Copy-Item .env.example .env
.venv/Scripts/python.exe -m uvicorn backend.app.main:create_app --factory --env-file .env --host 127.0.0.1 --port 8000 --workers 1
```

已有 `.env` 时保留原文件。另开终端：

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

打开 [第二版审核](http://127.0.0.1:5173/) 或 [数字人像测试](http://127.0.0.1:5173/jury)，两者共用侧栏和工作区样式。Windows 启动脚本位于 `scripts/`。审核固定模式支持四个预设案例，数字人像测试提供水杯与复印纸样例；固定模式不能审核任意新素材。

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
