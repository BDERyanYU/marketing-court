# 架构与模块边界

首版采用 React 前端、FastAPI 后端和 SQLite。主审核由固定流程控制；模拟法庭独立管理控辩和证据台账；消费者模拟按需运行。具体业务规则见[产品说明](../AI%20Marketing%20Court%20V1.0.md)。

```mermaid
flowchart TB
    UI[前端：上传 / 审核视图 / 模拟庭审 / 消费者陪审团] --> API[FastAPI：认证、项目与状态 API]
    API --> MATERIAL[素材管理与解析]
    MATERIAL --> EXTRACT[文字与视觉宣称提取]
    EXTRACT --> RETRIEVE[规则 / 平台政策 / 产品证据检索]
    RETRIEVE --> REVIEW[Workflow：结构化审核]
    REVIEW --> REWRITE[Workflow：局部改写与复核]
    API --> COURT[模拟法庭 Controller]
    COURT --> PROSECUTOR[控方 Agent]
    COURT --> DEFENSE[辩方 Agent]
    PROSECUTOR --> LEDGER[(Evidence Ledger)]
    DEFENSE --> LEDGER
    LEDGER --> JUDGE[独立法官复核]
    API --> PERSONA[Persona Compiler]
    PERSONA --> SCENARIO[Scenario Planner]
    SCENARIO --> SIM[隔离消费者模拟]
    SIM --> AGGREGATE[结果聚合与差异分析]
    MATERIAL --> DB[(SQLite；后续 PostgreSQL)]
    REVIEW --> DB
    REWRITE --> DB
    LEDGER --> DB
    JUDGE --> DB
    AGGREGATE --> DB
    DB --> API
```

`PolicyStore` 与企业提供的 `ProductEvidenceStore` 分开管理。模型输出先经过结构化校验和引用核查，才可写入业务状态。素材、数据库、密钥和客户 Persona 不进 Git。
