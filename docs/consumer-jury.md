# 用户画像派生与营销 A/B 模拟

配对模拟按 `报告 → 用户确认基础画像 → 主 Agent 选择理论并派生 → 独立评价 A/B → 汇总` 运行。两次评价沿用同一个成员的人格提示与购买情境。每次模型请求携带一版文案、基础画像和该成员的假设，因此两次评价各自从首次接触开始。

票投的是「看到这版文案后，是否愿意进一步了解产品」。程序汇总每版票数，并给出清晰度、信任、吸引力、购买考虑四项评分的个人变化。报告保留解释、误读、待核实事实和不确定性。结果适合找真人测试的假设，实际消费者行为需要外部验证。

## 统一启动

从 [项目根目录](../README.md)运行下列命令，使用已安装的 Python 3.12。

```sh
uv sync --locked --python 3.12 --no-python-downloads
.venv/bin/python -m marketing_court
```

打开 [营销模拟](http://127.0.0.1:8000/jury)，点「用水杯样例」加载报告和两版文案。确认提取的画像、选择成员数，然后运行 A/B 盲测。默认 `demo` 模式使用固定模型输出，走完整的 API、保存、恢复及计票。

真实模式可处理自己的报告。消费者模拟和庭审调用共用的 `backend/app/core/model_api.py`。报告文字和广告文案会发送给 DeepSeek，SQLite 保留提取的画像与引用、派生面板和模拟结果。可用 `MARKETING_COURT_DEEPSEEK_MODEL` 设置两边的模型，默认 `deepseek-flash`。

```sh
MARKETING_COURT_MODE=live DEEPSEEK_API_KEY_FILE="/absolute/path/to/deepseek-key.txt" \
  .venv/bin/python -m marketing_court
```

- 支持 UTF-8 文本、Markdown、DOCX 的段落与表格、可提取文字的 PDF。单个文件最多 8 MB，抽取正文上限 48,000 字符，PDF 上限 60 页。扫描件先转换成可复制文本。
- 画像字段区分报告支持、推断、未知和用户填写。每条报告支持的字段都需有原文引句。找不到合适的提取画像时，实时模式可手填后确认。
- 数据库默认是 `var/consumer-jury.sqlite3`，可用 `JURY_DB_PATH` 设置。刷新报告、面板或比较的页面地址可继续现有进度。终端按 Ctrl+C 可停止服务。

## 营销理论接入

设置 `JURY_THEORY_SKILL_FILE=/absolute/path/to/SKILL.md` 指向负责营销理论的同学交付的 Markdown 文件，随服务启动读取。传给主 Agent 的候选包含团队 Skill 的入口及内置 STP、JTBD、ELM、PKM。主 Agent 先选候选 ID，程序核对 ID 并取回对应正文，派生请求携带选中的内容。结果记录使用的理论来源及版本摘要。

团队 Skill 可以写适用场景、画像推导方法、允许引入的情境变量、假设标注和反例。文件内容作为营销知识材料传给模型。网页检索适配属于可选后续入口。

## API 与恢复

| 方法与路径 | 输出 |
|---|---|
| `POST /api/jury/reports` | 上传字段 `file`，返回报告 ID 和待确认画像 |
| `GET /api/jury/reports/{report_id}` | 读取提取的画像、证据摘录和处理方式 |
| `POST /api/jury/panels` | 传 `report_id` 和 `persona_id`，或传 `manual_persona`，返回固定面板、抽样计划和理论版本 |
| `GET /api/jury/panels/{panel_id}` | 读取抽样计划、固定成员和人物假设 |
| `POST /api/jury/comparisons` | 传 `panel_id`、`original_text`、`revised_text`，创建比较 |
| `POST /api/jury/comparisons/{id}/advance-members` | 传 `expected_index`，并行评价下一批成员 |
| `POST /api/jury/comparisons/{id}/advance` | 传 `expected_index`，执行一次独立评价 |
| `GET /api/jury/comparisons/{id}` | 读取已保存反馈，完成后包含配对结果与汇总 |

报告提取用一次模型请求。默认派生 N 位成员需 N + 3 次请求，包括选择理论、生成抽样维度、制定联合配额和逐人生成规格。A/B 要做 2N 次评价。页面每批并行处理最多 `JURY_MAX_CONCURRENT_MEMBERS` 位成员，默认 2。同一成员按既定顺序逐版评价，每次用相同的人设和一次独立的模型请求。真实模式共用项目配置的 Key。上限适用于一个服务进程内所有消费者评价。

每条结果按成员 ID 和文案版本在 SQLite 事务中保存。并行结果可能乱序返回，`exposures` 的长度表示已保存条数，`next_index` 指向尚未完成的最早评价。某条失败后，已保存的结果可直接恢复，继续时只提交缺失的评价。

## TinyTroupe 派生

默认派生使用 `tinytroupe_panel.py`。它调用从固定版本 TinyTroupe 移植的维度规划、联合配额与人物生成提示词，以及原工厂的配额展开代码。上游来源和 MIT 许可证保存在 `backend/app/jury/vendor/`。[上游画像工厂](https://github.com/microsoft/TinyTroupe/blob/7ce8be378a37ee73f9745d6781452712318afa04/tinytroupe/factory/tiny_person_factory.py) · [上游人物模板](https://github.com/microsoft/TinyTroupe/blob/7ce8be378a37ee73f9745d6781452712318afa04/tinytroupe/factory/prompts/generate_person.mustache)

用户确认报告画像后，选中的营销理论随画像传入派生器。演示支持一到三个离散维度。例如，水杯样例用「地铁灯箱、低证据关注度」安排两席，用「商品详情页、高证据关注度」安排一席。席位数仅用于构成本次模拟。程序校验取值与人数，按配额展开成员，并将计划与人物规格一同保存。

人物规格由现有 DeepSeek 适配器生成，A/B 由项目的独立评价执行器从同一份冻结规格分别运行。此次移植范围是画像派生。页面默认使用 TinyTroupe，API 还可显式传 `sampling.mode` 为 `random` 或 `full` 运行本地对照。

## 测试

从项目根目录运行 `.venv/bin/python -m pytest -q`。覆盖上传解析、报告引句检查、选择团队 Skill、TinyTroupe 联合配额和校验、固定成员 A/B 的请求隔离、计票、重启恢复、实时配置和演示模式。
