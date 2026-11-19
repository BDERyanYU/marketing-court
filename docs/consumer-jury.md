# 数字人像测试

配对模拟按 `报告正文 → TinyTroupe 派生 → 独立评价 A/B → 汇总` 运行。用户可补充已知画像。两次评价沿用同一份原版人物 JSON，每次模型请求携带一版文案，从首次接触开始。

票投的是「看到这版文案后，是否愿意进一步了解产品」。程序汇总每版票数，并给出清晰度、信任、吸引力、购买考虑四项评分的个人变化。报告保留解释、误读、待核实事实和不确定性。结果适合找真人测试的假设，实际消费者行为需要外部验证。

## 统一启动

从 [项目根目录](../README.md)运行下列命令，使用已安装的 Python 3.12。

```sh
uv sync --locked --extra ocr
.venv/Scripts/python.exe -m marketing_court
```

同时启动前端后，从侧栏进入 [数字人像测试](http://127.0.0.1:5173/jury)。该页面与项目素材共用导航、表单和面板样式。点「用水杯样例」加载报告和两版文案，保留「仅使用报告正文」，填写测试人像数（正整数，默认 3），再点「生成人像」和「运行 A/B 盲测」。可展开原版人物 JSON、逐人反馈及评分变化。默认 `demo` 模式使用离线模型响应，实际执行原版工厂、API、保存、恢复及计票。后端 8000 的 `/jury` 保留为原始独立工具，默认前端直接呈现新的 React 工作区。

真实模式可处理自己的报告。消费者模拟和素材审核调用共用的 `backend/app/core/model_api.py`。报告文字、配置的营销 Skill 和广告文案会发送给 DeepSeek。SQLite 保留报告正文、提取的画像与引用、派生面板和模拟结果，报告接口返回提取结果。可用 `MARKETING_COURT_DEEPSEEK_MODEL` 设置两边的模型，默认 `deepseek-flash`。

```sh
MARKETING_COURT_MODE=live DEEPSEEK_API_KEY_FILE="/absolute/path/to/deepseek-key.txt" \
  .venv/Scripts/python.exe -m marketing_court
```

- 支持 UTF-8 文本、Markdown、DOCX 的段落与表格、可提取文字的 PDF。单个文件最多 8 MB，抽取正文上限 48,000 字符，PDF 上限 60 页。扫描件先转换成可复制文本。
- 画像字段区分报告支持、推断、未知和用户填写。每条报告支持的字段都需有原文引句。创建面板可以直接使用报告正文，也可以选一个提取的画像或在真实模式手填画像。
- 统一服务的数据库默认是 `data/consumer-jury.sqlite3`，独立模拟服务默认使用 `var/consumer-jury.sqlite3`，均可用 `JURY_DB_PATH` 设置。刷新报告、面板或比较的页面地址可继续现有进度。终端按 Ctrl+C 可停止服务。

## 营销理论接入

仓库自带经过水杯样例验证的[消费者画像派生理论 Skill](../skills/persona-derivation/SKILL.md)。在项目根目录运行以下命令即可带上这份 Skill 启动，并在营销模拟页加载水杯样例。

```sh
JURY_THEORY_SKILL_FILE="$PWD/skills/persona-derivation/SKILL.md" \
  .venv/Scripts/python.exe -m marketing_court
```

新的 Skill 可以各放在一个 `skills/<名称>/SKILL.md` 中。将 `JURY_THEORY_SKILL_FILE` 指向要用的文件，重启服务后生效。加载器把 Skill 的正文与报告一起交给原版工厂的 `sampling_space_description`，并放进用于生成单个人物的 `context`。系统提示词由原版工厂构造，面板记录 Skill 文件名和内容版本摘要。

团队 Skill 可以写适用场景、营销理论如何判断值得分析的差异，以及标注派生假设的方法。文件读取的是 Markdown 正文。未配置 Skill 时，工厂直接根据报告和用户可选补充的画像派生。

## API 与恢复

| 方法与路径 | 输出 |
|---|---|
| `GET /api/jury/examples/copier-paper` | 用户提供的德国复印纸调研正文、A/B 文案和未核验说明 |
| `POST /api/jury/reports` | 上传字段 `file`，返回报告 ID 和待确认画像 |
| `GET /api/jury/reports/{report_id}` | 读取提取的画像、证据摘录和处理方式 |
| `POST /api/jury/panels` | 传 `report_id`，可选传 `persona_id` 或 `manual_persona`，返回固定面板、抽样计划及 Skill 版本 |
| `GET /api/jury/panels/{panel_id}` | 读取抽样计划和成员的人物规格 `members[].specification` |
| `POST /api/jury/comparisons` | 传 `panel_id`、`original_text`、`revised_text`，创建比较 |
| `POST /api/jury/comparisons/{id}/advance-members` | 传 `expected_index`，并行评价下一批成员 |
| `POST /api/jury/comparisons/{id}/advance` | 传 `expected_index`，执行一次独立评价 |
| `GET /api/jury/comparisons/{id}` | 读取已保存反馈，完成后包含配对结果与汇总 |

报告提取用一次模型请求。原版工厂依次规划维度和联合组合，还会为角色生成姓名、人物规格和简介。A/B 要做 2N 次评价。页面每批并行处理最多 `JURY_MAX_CONCURRENT_MEMBERS` 位成员，默认 2。同一成员按既定顺序逐版评价，每次用相同的人设和一次独立的模型请求。真实模式共用项目配置的 Key。上限适用于一个服务进程内所有消费者评价。

每条结果按成员 ID 和文案版本在 SQLite 事务中保存。并行结果可能乱序返回，`exposures` 的长度表示已保存条数，`next_index` 指向尚未完成的最早评价。某条失败后，已保存的结果可直接恢复，继续时只提交缺失的评价。

## TinyTroupe 派生

默认派生直接调用 `vendor/tinytroupe` 中的原版 `TinyPersonFactory`。工厂完成维度规划、联合配额、样本展开和人物实例化。成员的 `specification` 可以交给 `TinyPerson.load_specification`。上游源码固定在 `7ce8be378a37ee73f9745d6781452712318afa04`，MIT 许可证随源码保留。[上游画像工厂](https://github.com/microsoft/TinyTroupe/blob/7ce8be378a37ee73f9745d6781452712318afa04/tinytroupe/factory/tiny_person_factory.py) · [上游人物模板](https://github.com/microsoft/TinyTroupe/blob/7ce8be378a37ee73f9745d6781452712318afa04/tinytroupe/factory/prompts/generate_person.mustache)

面板保存工厂给出的维度、联合方案和人物规格。水杯报告中的防漏、重量和清洗可以作为候选维度的来源。配置营销 Skill 后，模型可以结合用途和证据核查等线索提议跨维度组合。原版工厂决定维度的数量、范围和候选取值。席位数是本次模拟安排。

API 的 `sampling.mode` 还可显式设为 `random` 或 `full`。在这两种模式下，项目先确定离散组合，再交给原版工厂生成每个人。已保存的旧面板仍可恢复对应实验。

本地对上游工厂作了一处兼容修正：成功生成角色但关闭详细日志时，不再错误记录为失败；生成失败时也不会先读取空角色的简介。其余派生流程沿用固定的上游版本。

## 测试

从项目根目录运行 `.venv/bin/python -m pytest -q`。覆盖无明确画像的报告直接派生、Skill 进入同一条原版提示流程、TinyTroupe 联合配额、固定成员的 A/B 请求隔离、计票、恢复和演示模式。

## 复印纸样例

点击“用复印纸样例”同时载入用户提供的《测试用-复印纸-用户画像调研报告.docx》正文和两版 Amazon Basics 文案。正文及文案保存在 `backend/app/jury/examples/copier-paper-*.txt`；报告四类客群为企业行政采购、公共机构/非营利组织、环保居家办公、家庭与学生。A 版的 `(5 Rivers)` 及 B 版 Blue Angel 声明按用户输入保留，不代表系统已核实产品事实、认证或报告中的法规描述。

实时模式正常提取报告并派生人像；固定模式使用复印纸专属预设数据，并校验两版文案与报告对应，避免混用水杯样例。固定反馈不是对 B 版有效性的真实证据。水杯 `/api/jury/demo` 接口保持兼容。
