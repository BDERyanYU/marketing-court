# Marketing Court 首页

按用户提供的 `marketing-court-landing-prompt.md` 制作，默认英文。视觉使用纸灰 `#EEF0F2`、墨黑 `#0F1115`、正文灰 `#2A2E35`、代码灰 `#7A7F88`、扫描橙 `#FF5A1F` 和浅橙 `#FFE1D3`。Inter 用于界面，Newsreader 正体与斜体用于标题，IBM Plex Mono 用于审核文本；官方 Latin WOFF2 嵌入 HTML。

布局：56px 顶栏只保留放大的品牌标志；居中的双行标题、缩小的简介和深灰色按钮；下方全宽卡片传送带。广告位于扫描线右侧，审核摘录在左侧对应位置出现。全页唯一重点是中心扫描线和随卡片位置同步的橙色粒子。

```text
放大的品牌标志
                         双行标题
                         产品简介
                         审核入口
                         风险计数
        审核摘录          │        GreenLint 广告卡片
        向左渐隐          │        连续传送，可反向拖动
```

保留指定稿中的衬线斜体标题、扫描动效和渐变卡片。按用户随后批注删除 Review、Consumer jury、Case files、Docs、GitHub、Enter the jury、Start a review 和左上角说明标签。唯一功能入口是深灰色 Open the court，点击后进入原项目主页面。正文正常换行；短屏调整卡片起点避免覆盖操作按钮。

首页为单个 HTML，原生 CSS/JavaScript，无新增依赖。只有六张指定 CDN 背景图片需要联网；页面文字、字体、图形和动画均可离线呈现。审核摘录、计数及示例规则编号是视觉演示，非实际 API 审核，不作为法规原文。

`/` 显示欢迎页，`/review` 加载原项目主页面，`/jury` 保持数字人像工作区。三个独立 HTML 入口随 Vite 一起打包，开发/产物预览精确映射路径；静态托管可直接使用目录入口。`?ui=v1`、`?ui=v2` 和 `?ui=v3` 保留。真实入口使用普通链接，欢迎页不调用后端。持续动画支持暂停、拖动、横向滚轮和键盘左右键，尊重减少动态效果设置。

验证：类型检查与生产构建通过；开发及生产预览均通过 `tests/landing-browser.cjs`，覆盖六张卡片及各自计数、扫描中心对齐、暂停、键盘与反向拖动、离线字体、减少动态效果、六种屏幕宽度，以及欢迎页 → Open the court → 原主页面 → 数字人像 → 原主页面。原审核浏览器回归通过上传、重试、改写、导出及旧版隔离；原数字人像浏览器回归通过 A/B 和刷新恢复。截图位于被 Git 排除的 `test-results/landing-browser/`、`test-results/landing-production/`。
