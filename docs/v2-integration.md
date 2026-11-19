# 第二版整合验收记录

验收日期：2026-11-20（北京时间）。整合分支：`codex/v2-tinytroupe-integration`。

## 版本范围

以现有第二版审核功能为准，合入朋友分支 `codex/tinytroupe-marketing-skill` 的 `4b54e8c`：TinyTroupe 原生画像、营销理论文件和并行消费者 A/B 反馈。原有重试、OCR、素材版本与审核恢复保留。默认页面恢复第二版，第一版审核布局仍可通过 `?ui=v1` 查看，第三版圆桌工作区保留在 `?ui=v3`。

按最新决定移除模拟法庭：删除庭审服务、API、控辩和法官角色、输入模型、案件存储实现、前端页面、异议入口、专用样式、示例和测试。审核演示素材改为独立 fixture。项目名称、旧配置变量和数据库文件名保持兼容；旧数据库中的历史表不再读取，也不执行破坏性清理。

整合在独立工作目录和分支完成，审核数据库、消费者数据库与上传文件使用副本。`main` 与原工作目录未改动，等用户验收后再合并。

## 已通过的检查

| 检查 | 结果 |
|---|---|
| Python 自动测试 | 82 通过，1 跳过；跳过项为需显式启用的 OCR 测试 |
| TypeScript 与 Vite 生产构建 | 通过 |
| 第二版浏览器回归 | 上传参数、失败重试入口、原图坐标、改写、JSON 下载、刷新恢复、第一版兼容；7 种屏宽无横向溢出 |
| GreenLint 案例 | 2 个负面与 1 个正面结果、市场标签、原文选中、规则、改写、刷新、JSON 下载及手机布局通过 |
| 项目素材浏览器回归 | 4 个案例同库、9 个市场、10 个商品类别、联合审核、同项目纯文案再次审核、刷新恢复、未覆盖市场提示通过 |
| 真实 DeepSeek 审核 | `deepseek-flash` 完成 PaddleOCR 图片识别、带坐标风险、联合审核、纯文案审核、一次改写复核和报告保存 |
| 消费者模拟浏览器回归 | 3 个原生人物 JSON、并行 A/B 的 6 条反馈、3 组配对结果、刷新恢复及手机布局通过 |
| 真实 DeepSeek 消费者模拟 | 报告提取、配置营销理论后原生工厂派生 1 人、独立 A/B 两次评价、配对汇总与读回一致通过 |
| 法庭移除 | 统一服务不再注册案件、异议和法庭输入接口；报告不再导出庭审记录 |

上游 TinyTroupe 留有 3 条 Pydantic 弃用提示，不影响当前运行。工厂成功生成角色的日志条件已作局部修正，避免误报失败。真实模型演练已完成；自动测试中的显式 OCR 测试没有重复启用。

本机验收输出保存在忽略提交的 `test-results/`：`live-report.json`、`live-consumer-integration.json`、`v2-browser/`、`greenlint-browser/`、`materials-browser/`、`consumer-browser/`。这些文件含本机运行记录，不上传仓库。

## 预览与复查

整合预览为 <http://127.0.0.1:5180/>，消费者模拟为 <http://127.0.0.1:5180/jury>，后端为本机 8020 端口。原 5173 预览仍为此前工作目录。启动方式见 README；此端口安排用于隔离验收。

```powershell
.venv/Scripts/python.exe -m pytest -q
cd frontend
pnpm build
```

真实模型演练需已启动实时后端，会产生模型请求：

```powershell
.venv/Scripts/python.exe scripts/live-smoke.py --url http://127.0.0.1:8020
.venv/Scripts/python.exe scripts/live-consumer-smoke.py --url http://127.0.0.1:8020
$env:APP_URL='http://127.0.0.1:5180'
$env:API_PROXY_URL='http://127.0.0.1:8020'
node tests/materials-browser.cjs
```

固定案例回归应指向独立的 demo 后端。`greenlint-browser.cjs` 不设置 `API_PROXY_URL` 时直接使用预览服务的代理，以验证真实文件下载；浏览器请求拦截会使 Chromium 的附件下载被取消。

## 当前适用边界

英国 CMA 环保规则仅为有限摘录。其他市场在规则未接入时只提取宣称，不给出合规批准。消费者结果是 AI 模拟；画像和营销理论不能替代真实市场调研。图像语义与产品证明自动核验不在本次整合范围内。
