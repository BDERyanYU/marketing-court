# AI Marketing Court · 庭审 P0

从一条已完成的环保广告审核风险开庭。控方和辩方交锋两轮，再由独立的裁判请求给出模拟风险复核意见。调度、发言和证据快照由服务端保存在 SQLite。发言依据是案卷中的文案、规则摘录和企业证据状态，投放审批由人工负责。

## 统一启动

从 [项目根目录](../README.md)统一启动，使用已安装的 Python 3.12。

```sh
uv sync --locked --python 3.12 --no-python-downloads
.venv/bin/python -m marketing_court
```

打开 [接口操作页](http://127.0.0.1:8000/docs)。默认 `demo` 模式预置一条风险 `demo-eco-bottle`，控辩和裁判返回固定演示数据。API 响应的 `mode` 和 `model` 会注明来源。

真实模式统一配置 DeepSeek 官方接口。可以直接引用已有的密钥文件。

```sh
MARKETING_COURT_MODE=live DEEPSEEK_API_KEY_FILE="/absolute/path/to/deepseek-key.txt" \
  .venv/bin/python -m marketing_court
```

实时模式默认选择 `deepseek-flash`，可通过 `MARKETING_COURT_DEEPSEEK_MODEL` 配置。每次角色调用会将当前案件材料和所需的发言上下文发送给 DeepSeek。密钥仅在服务端读取。

## 走完一个案件

1. 调用 `POST /api/risks/demo-eco-bottle/appeals`，保存返回的 `case_id`。
2. 调用 `POST /api/cases/{case_id}/advance`，请求体例如 `{"expected_step":"prosecution_1"}`。每次把响应里的 `next_step` 传入下一次请求。
3. 本案按 `prosecution_1 → defense_1 → prosecution_2 → defense_2 → judgment` 运行。完成后 `status` 为 `completed`，`next_step` 为 `null`，含四条发言和一条裁判建议。
4. 要验证恢复，保存第一轮控方后停止服务，使用同一 `COURT_DB_PATH`、模式和模型重启。调用 `GET /api/cases/{case_id}`，从 `defense_1` 继续。数据库默认在 `var/court.sqlite3`。

遇到模型超时或引用校验失败时，接口返回 502，案件仍停在原步骤。已提交步骤的重试返回现有记录。单进程内同一案件一次只运行一个推进请求。SQLite 在同一个事务里写入发言和下一步。如果模型已经回复、进程在数据库提交之前退出，恢复可能再次调用当前角色。

## 审核侧对接

审核完成后，把对应风险适配成 [开庭输入样例](../examples/court-input.json)，调用 `PUT /api/court-inputs/{risk_id}`。之后审核页面仅需按 `risk_id` 发起庭审。接口定义可从 [OpenAPI](http://127.0.0.1:8000/openapi.json) 读取，模型为 `CourtInput`。

| 字段 | 约定 |
|---|---|
| `risk_id`、`review_id`、`asset_version_id` | 分别指向完成的风险、审核和原文版本。路径与请求体的 `risk_id` 相同。 |
| `original_text`、`claim_quote`、`market` | 该次审核的完整原文、其中逐字一致的风险片段和两位大写市场代码。英国用 `GB`。 |
| `assessment`、`reason` | 审核侧状态和理由。本例为 `requires_substantiation`。 |
| `rule_pack_version`、`citations[]` | 本次检索实际使用的规则版本和摘录。每条含案卷内唯一的 `source_id`、`excerpt` 和 `url`。审核侧负责核对来源及适用性。 |
| `product_evidence_status` | 当前 P0 支持 `not_supplied`，表示该次审核未收到可供引用的企业证明。 |

同一 `risk_id` 重交相同输入会成功。风险、文案或规则版本变化时，使用新的风险 ID。开庭持有一份独立快照，后续按快照校验模型引用。实时模式可推进审核侧导入的案件，演示脚本对应预置水杯风险。示例也是一个固定版本，改版时应分配新的示例风险 ID。

## 组件与验证

文件划分按入口、总控、独立角色和状态存储划分。庭审按回合使用 SQLite 事务保存发言与状态。

- `backend/app/court/main.py` 和 `api.py` 把庭审路由装配到产品入口。
- `backend/app/court/controller.py` 组装角色输入、按步推进、检查引用和回应关系。
- `prosecutor.py`、`defense.py`、`judge.py` 分别定义角色。裁判使用独立请求，输入是案卷事实和已保存的控辩发言。
- `models.py` 定义接口和结果结构，`repository.py` 负责状态持久化，`demo.py` 提供固定案例的演示输出。DeepSeek 接入由产品共用的 `backend/app/core/model_api.py` 提供。

运行 `.venv/bin/python -m pytest -q` 验证对接字段、两轮顺序、重启恢复、重复请求和错误回合的重试。演示规则取自 [英国 CMA《Green Claims Code》](https://www.gov.uk/government/publications/green-claims-code-making-environmental-claims/environmental-claims-on-goods-and-services)。模型接口参照 [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)。
