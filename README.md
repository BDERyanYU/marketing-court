# AI Marketing Court

AI Marketing Court 是面向跨市场营销素材的证据驱动审核原型。当前可以运行两轮模拟庭审，以及基于市场调研画像的消费者文案 A/B 模拟。广告素材解析、结构化审核和单项改写的整体范围见 [产品说明](AI%20Marketing%20Court%20V1.0.md)。

## 运行水杯样例

在仓库根目录用 [uv](https://docs.astral.sh/uv/) 和已安装的 Python 3.12 启动。

```sh
uv sync --locked --python 3.12 --no-python-downloads
.venv/bin/python -m marketing_court
```

打开 [项目首页](http://127.0.0.1:8000/)。庭审接口在 [/docs](http://127.0.0.1:8000/docs)。到 [/jury](http://127.0.0.1:8000/jury) 点「用水杯样例」，从报告正文派生角色并比较两版文案。默认使用固定演示数据，同时评价最多两位成员，每条反馈生成后立即保存。按 Ctrl+C 停止服务。

要使用真实模型，把密钥文本文件路径传给同一个启动命令。

```sh
MARKETING_COURT_MODE=live DEEPSEEK_API_KEY_FILE="/absolute/path/to/deepseek-key.txt" \
  .venv/bin/python -m marketing_court
```

消费者 A/B 并发上限可通过 `JURY_MAX_CONCURRENT_MEMBERS` 设置。共享设置见 [.env.example](.env.example)。测试命令为 `.venv/bin/python -m pytest -q`。

## 组件

- `backend/app/main.py` 加载庭审和消费者模拟路由。
- `backend/app/core/model_api.py` 统一接入 DeepSeek，并校验结构化输出。
- `backend/app/court` 按回合保存案件、发言和判决建议。详见 [庭审接口](docs/court.md)。
- `backend/app/jury` 提取报告画像，复用 TinyTroupe 派生成员，并分别评价两版广告。详见 [消费者模拟](docs/consumer-jury.md)。
- `frontend` 提供 React 导航骨架。模块规划见 [架构说明](docs/architecture.md)。

## 开发约定

- 共享对象使用稳定的 `claim_id`、`risk_id`、`source_id`、`asset_version_id`。
- 审核、庭审和模拟结果都要保留来源及版本；法官建议不覆盖原审核记录。
- 上传素材、客户文档、数据库和密钥只保存在本地运行目录，已由 `.gitignore` 排除。
- AI 辅助审核不构成法律意见；模拟消费者输出不代表真实市场调查。
