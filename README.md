# AI Marketing Court

AI Marketing Court 是面向跨市场营销素材的证据驱动审核原型。系统计划支持广告素材解析与定位、结构化风险审核、单项改写与复核、模拟法庭，以及基于企业 Buyer Persona 的可选消费者模拟。

本仓库目前是**项目骨架**，尚未实现审核、模型调用、法律规则库或消费者模拟。产品范围和验收标准见 [产品说明](AI%20Marketing%20Court%20V1.0.md)，模块边界见 [架构说明](docs/architecture.md)。

## 仓库结构

- `backend/app/api`：FastAPI 路由与请求模型
- `backend/app/core`、`backend/app/models`：配置、模型适配器与共享数据契约
- `backend/app/workflows`、`backend/app/services`：固定审核流程与素材处理服务
- `backend/app/court`：模拟法庭调度、角色与证据台账
- `backend/app/jury`：Persona、情境与模拟结果
- `backend/app/data/policies`：有出处和版本的规则卡
- `frontend/src/pages`、`frontend/src/components`：各页面及界面组件
- `tests/fixtures`：人工核验案例与来源
- `docs`：架构和演示资料

## 本地启动骨架

需要 Python 3.11+、[uv](https://docs.astral.sh/uv/)、Node.js 20+ 和 pnpm。

```bash
uv sync
uv run uvicorn backend.app.main:app --reload
```

另开终端：

```bash
cd frontend
pnpm install
pnpm dev
```

后端的 `/health` 只用于检查服务是否启动。前端是页面导航骨架；业务功能会按产品说明逐步开发。

## 开发约定

- 共享对象使用稳定的 `claim_id`、`risk_id`、`source_id`、`asset_version_id`。
- 审核、庭审和模拟结果都要保留来源及版本；法官建议不覆盖原审核记录。
- 上传素材、客户文档、数据库和密钥只保存在本地运行目录，已由 `.gitignore` 排除。
- AI 辅助审核不构成法律意见；模拟消费者输出不代表真实市场调查。
