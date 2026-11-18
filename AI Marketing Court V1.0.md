# AI Marketing Court V1\.0

## 执行摘要

### 0\.1 产品定位

AI Marketing Court 是一套面向企业跨市场营销素材的**可视化审核、证据驱动复核与消费者反应预评估系统**。企业上传广告海报、文本或文件并指定目标市场、商品类别、投放渠道，系统识别其中的营销宣称，依据适用法规、平台规则以及企业提供的产品证明材料，标注风险并生成可追溯的修改建议。

有争议时，用户可就单个风险项启动“模拟法庭”：控方与 AI 律师自主多轮辩论，用户随时介入或提交新证据，独立法官模型给出**非正式风险复核意见**。用户还可主动上传企业已有的 Buyer Persona 文档，启用“消费者陪审团”，模拟这些目标消费者在不同购买/观看情境下对原始广告及修改版本的理解与疑虑。

**核心主张：审核可以被质疑，结论必须有证据；营销效果可以先模拟，但不能冒充真实市场数据。**

### 0\.2 产品结构与技术决策

**不采用“全部 Agent 化”**：主审核的执行顺序固定，程序控制更可追溯、更便宜、更易测试。独立 Agent 主要用于反驳与自主选择证据检索策略的多轮庭审。

### 0\.3 明确不做的事

- 不承诺“自动判定合法/违法”，不提供法律授权或自动批准投放。

- 不将 LLM 自评置信度当作准确率，也不把模拟消费者的票数当作真实人口比例。

- 首版不开发生成式修图引擎、自动替换海报字体/背景、覆盖全球所有市场的法规库、复杂微服务体系。

- 没有实证验证前，不声称多 Agent 辩论比单模型审核必然更准确。

## 核心用户与使用流程

**主要用户**：跨境电商企业营销团队、出海品牌内容运营、广告代理商的合规与创意协作人员。

**用户路径 A｜常规审核**：上传素材 → 选择国家/地区、投放平台、产品类别 → 解析画面与宣称 → 检索相关规则/产品证据 → 逐项风险审核 → 原图标注、解释与引用 → 生成局部改写建议 → 改写复核 → 导出报告。

**用户路径 B｜质疑结论**：点击风险项“提出异议” → 生成案件档案 → 选择自行辩护或 AI 律师 → 控辩自主多轮交锋 → 可随时暂停、提交证据、追加轮数 → 裁判根据证据独立复核 → 回写“复核建议”，必要时创建新审核版本。用户不能通过模拟辩论直接取得法律合规批准。

**用户路径 C｜消费者陪审团**：上传已有 Persona 文件（可以只有一个） → 解析并确认画像 → 选择观看情境和模拟规模 → 多个隔离的模拟消费者先“盲看”原始广告并独立回答 → 分析共性、分歧与不确定性 → 可选择某个模拟消费者作为庭审证人 → 将同样方法应用于修改版 B 进行定性对比。

**用户路径 D｜版本闭环**：Review V1 → 用户采纳/编辑某项改写 → 形成 Creative V2 → 重新审核相关宣称 → 可分别运行模拟消费者测试 → 比较“风险变化 / 论据变化 / 消费者解读变化”。

## 总体架构

![image\.png](图片和附件/image.png)

### 2\.1 选型（建议）

- **前端**：React \+ TypeScript \+ Vite \+ Tailwind CSS；素材预览用 SVG overlay 画框，若后期需要自由编辑再选 React Konva。多页 PDF 预览可使用 PDF\.js。

- **后端**：Python 3\.11\+、FastAPI、Pydantic、httpx、uv；标准 REST API，长任务的执行过程经 SSE 发送事件。

- **模型层**：可替换的 `LLMProvider` 适配器，首版接入一个支持图像输入与 JSON Schema 结构化输出的 API；审核与改写使用不同提示模板，禁止将模型原始文本直接作为数据库状态。

- **文档/坐标**：PDF 原生文本与坐标优先使用 PyMuPDF；DOCX 可抽取段落和表格，但没有可靠的页面坐标，默认使用段落高亮；图片使用 PaddleOCR 取得文字行及四点坐标，多模态 LLM 负责整体语义与非文字视觉宣称。

- **数据层**：SQLite \+ SQLAlchemy/SQLModel 适合首版单机演示；文件存本地项目目录（不上传代码仓库），生产化再迁移到对象存储/PostgreSQL。

- **RAG**：首版以**小而可信的规则卡库**为基础，使用市场/行业/生效时间过滤 \+ 关键词/BM25 检索；有足够资料后再添加向量召回与 reranker。不要为少量规则引入重型向量基础设施。

- **任务执行**：首版 FastAPI 后台任务 \+ 数据库状态 \+ SSE；如有持久并发需求，再引入 Redis / 队列；避免为了演示搭建多套服务。

## 共享数据契约与审计机制

**原则：整个系统围绕稳定的 ****`claim_id`****、****`risk_id`****、****`source_id`****、****`asset_version_id`**** 运转。** 主审核、庭审、陪审团读取同一份标准化素材与审核证据，模块彼此不依赖对方的自然语言输出。

### 3\.1 最小数据实体（暂定）

- `Project`：企业/活动、目标市场、商品类别、投放平台、语言。

- `Asset` \+ `AssetVersion`：原始文件、文件哈希、类型、尺寸、页面、版本与存储地址。

- `TextAnchor`：`anchor_id, asset_version_id, page, text, polygon, coordinate_space, extraction_method, extraction_score`。`polygon` 由 OCR/文档解析工具产生；无位置时为空。

- `Claim`：`claim_id, asset_version_id, claim_text, claim_type, anchor_ids[], context, product_fact_refs[]`；允许一条宣称跨多个文字块，或存在仅视觉表达的宣称。

- `PolicySource`：`source_id, title, jurisdiction, platform, product_scope, effective_from, effective_to, issuer, url, retrieved_at, checked_at, original_text, content_hash, version`。

- `ProductEvidence`：用户提交的认证、检测、内部规格等，记录提供者、文档引用及核验状态；与法律来源严格分库标识。

- `RiskItem`：风险类别/严重度/判断状态、受影响宣称、法规与证明引用、解释、修改建议、原始审核版本。

- `CourtCase`、`DebateTurn`、`EvidenceLedgerEntry`、`Judgment`：保证庭审可暂停、恢复和复核。

- `PersonaSource`、`PersonaProfile`、`Scenario`、`SimulationResponse`：严格区分文档明确的事实、理论推断及未知信息。

- `AuditEvent`：谁、何时、使用哪个模型与规则版本，改变了什么状态；记录失败与用户人工修订。

### 3\.2 `RiskItem` 示例（暂定）

```JSON
{"risk_id": "R001","review_id": "REV001","asset_version_id": "AV001","claim_ids": ["C001"],"anchor_ids": ["T004"],"category": "legal_rule_risk","severity": "high","assessment": "requires_substantiation","reason": "泛化环保宣称，现有材料不足以支持整体性表述","policy_source_ids": ["EU2024_825_A1"],"product_evidence_ids": [],"evidence_gaps": ["产品环保表现的适用证明"],"suggested_rewrite": "改用能够核实的具体材料属性","workflow_status": "open","human_approval": "not_requested"}
```

`severity`（风险严重程度）必须与 `assessment`（证据与判断状态）分开。例如可能是 `severity=high, assessment=insufficient_information`。模型给出的自信分数不得用作真实校准概率。

**状态规则**：`open → under_appeal → review_recommended → human_reviewed/closed`；法官只写新的 `Judgment` 和建议状态，不直接篡改原始 `RiskItem`。所有修改采用版本追加。前端“标绿”仅表示某一版本已完成特定检查，绝不等于法律批准。

## 主体审核 Workflow：各子模块详细实现

### 4\.1 上传与任务初始化

**输入**：PDF/DOCX/PNG/JPG/文本；目标司法辖区、营销渠道、商品类别、宣传语言；可选产品资料、广告平台、营销目标。
**处理**：限制大小/页数、校验 MIME 与文件签名、病毒扫描或至少拒绝可执行内容；计算 SHA\-256；创建 AssetVersion；对缺少的关键上下文显示需要确认状态。
**输出**：`ReviewRequest` \+ `AssetVersion`。
**失败处理**：超限、解析失败与不支持的格式应阻止后续自动判断并给出明确原因。

### 4\.2 多模态解析与可视化定位

1. **PDF 有文本层**：通过 PyMuPDF 读取 spans/blocks、页码与 bbox，保留页面尺寸。

2. **图片或扫描 PDF**：调用 PaddleOCR 输出文本、`rec_polys`/`rec_boxes` 与 OCR 置信度，同时向多模态 LLM 提供原图，以识别图文关系、印章、标识、视觉暗示。

3. **DOCX**：解析段落、表格、图片与顺序；首版使用段落级定位，不承诺像素级原图定位；如要分页/像素坐标，需可靠的渲染或转换流水线。

4. **内容归一**：存储 page、原始尺寸、文字 anchor 与多模态摘要；让 LLM 生成可审查的 `Claim[]`，包括明确文字宣称、由图像/文字共同形成的隐含宣称。

5. **宣称映射**：以 `anchor_ids` 关联 LLM 识别的宣称与 OCR/原生文字坐标。先做精确文本匹配，再做规范化匹配与有限 fuzzy match；低匹配分数不能强行标注，只在右侧风险列表展示“定位待确认”。

6. **前端展示**：统一按原始页宽高存归一化多边形，前端根据实际显示大小缩放。框选、滚动定位和风险列表双向联动；对于跨多行的风险显示多个框。非文字视觉风险可显示粗粒度区域，并提示视觉定位不确定性。

**要点**：多模态 LLM 负责“识别什么有问题”，OCR/文本解析负责“位于哪里”，前端负责“如何标红”；不能把模型猜测的坐标当作确定事实。

### 4\.3 宣称分类与法规/证据 RAG

**宣称分类**：环保、功效、健康、安全、价格/折扣、排名/比较、认证/背书、敏感人群、平台政策、文化表达等；根据广告可同时出现多个类别。

**检索的两套证据库**：

- `PolicyStore`：官方法规与监管指引、官方平台广告政策。每条规则卡必须有出处、生效时间、辖区、商品适用范围和具体条款；针对跨境市场，应核对实际投放国家而不是笼统使用“EU”替代所有国家执行差异。

- `ProductEvidenceStore`：企业提供的检测、认证、规格、产品数据等，标明“企业主张/第三方报告/已独立核验”的不同级别。上传材料只是证据候选，不是自动可信。

**执行逻辑**：每条 Claim 根据 `jurisdiction + product_scope + platform + claim_type + effective_date` 先做硬过滤，再关键词/全文检索召回候选，LLM 只对相关片段进行解释。每个审核结论必须关联至少一个明确来源，或标注 `source_missing`；引用前校验 `source_id`、段落与原文是否真实存在。

**版本性**：法律/政策过期或不确定时，标记需人工核实，不得自动降级为合规。检索到的网页、PDF 和用户文件都属于**不可信输入**，不可执行其中的指令。

### 4\.4 结构化风险审核

输入：`Claim + OCR/visual context + PolicySource[] + ProductEvidence[]`。
输出：`RiskItem[]`，并明确区分：

- `legal_rule_risk`：法规适用风险；

- `platform_policy_risk`：平台审核政策风险；

- `substantiation_gap`：营销宣称缺少证明；

- `cultural_localization_note`：语言文化适配建议，**不能冒充法律风险**。

对每项输出风险等级、法规事实、产品事实、推断链的简短可审计解释、来源编号、未核实前提、可操作修改。使用 JSON Schema/Pydantic 校验格式；对不存在的引用、越权结论、空洞理由进行程序层拒绝或降级。遇到规则冲突/地域不明/证据不足时返回 `needs_human_review`，不强行二选一。

### 4\.5 文案改写与二次复核

生成时保留企业营销意图、目标受众和真实产品信息，禁止发明材质比例、认证编号、试验结论；提供“谨慎改写 / 保留卖点 / 删除风险宣称”最多三种候选。每条候选附变更原因与被保留的产品事实，用户可局部采纳。改写只生成文案层的预览；扁平化 PNG/JPG 原图的真实重排、背景修补与字体恢复属于后续高级编辑功能。

对候选文案重新跑相关 Claim 的审核。流程不能为“降风险”而无限循环，默认至多一次自动复核，失败时显示具体风险和待补材料。提交新文件或人工编辑后创建 `AssetVersion V2`，原版本可回溯。

### 4\.6 审核报告

每份报告至少包含：目标市场/渠道/商品、素材与规则版本、每条风险及定位、来源链接、产品证据状态、未解决问题、原文与建议文案对照、人工确认状态、免责声明。首版输出页面报告与 JSON，PDF 下载放到后续优先级。

## 模拟法庭：受控多 Agent 辩论

### 5\.1 启动与数据输入

用户从一条 `RiskItem` 点击“提出异议”，创建 `CourtCase(risk_id, review_snapshot, policy_snapshot, evidence_snapshot)`，避免辩论期间原案例被悄悄改写。支持两种参与模式：用户亲自辩护；AI 律师代辩（用户仍可发言与补充文件）。

### 5\.2 角色职责

- **控方 Agent（Prosecutor）**：提出风险依据，对辩方的事实与法律解释提出可检查的质疑；允许撤回某项指控，禁止为获胜捏造条款。

- **辩方 Agent（Defense Counsel）**：质疑适用性、事实前提与证据充足性，尝试提供反证或更窄的合法宣传解释；承认对方成立的论点，不承担真实法律代理职能。

- **Court Controller（调度器，不必是 Agent）**：维护当前争点、发言顺序、工具权限、轮数/时间/Token 预算、用户插话、重试与中断；默认轮流发言但允许主动要求补证或转向新争点。

- **Debate Monitor（规则与结构化检查）**：跟踪“新证据、新问题、已解决争议、重复程度、偏题、未解决问题”。模型可辅助分类，但是否触发硬停止由代码控制。

- **法官（Judge）**：在辩论停止后，独立读取原始素材、经核验的规则和证据、争议点与反证；输出非正式风险复核建议。不能把“控方更有说服力”当作法律依据。

### 5\.3 多轮策略

一轮定义为：控方一回合 \+ 辩方一回合 \+ Monitor 更新。默认**智能庭审：至少 2 轮、最多 5 轮**（工程初始值、非研究最优结论）；用户可选快速 1–2 轮、深度最多 8 轮；可暂停/终止、提高预算、提交证据后恢复。另设硬性模型调用次数、Token 和最长执行时间上限。

```Python
while not case.stop_requested:
    prosecutor_turn = run_prosecutor(case.visible_state)
    verify_citations_and_append(prosecutor_turn)
    defense_turn = run_defense(case.visible_state)
    verify_citations_and_append(defense_turn)
    update_issue_board_and_evidence_ledger()
    if budget_exhausted() or user_requested_verdict(): breakif all_material_issues_resolved(): breakif round_count >= 2 and no_material_progress_for(2): break*# 争点未解决时，结案可返回“待补证”，而非“无风险”*
judgment = run_independent_judge(case.evidence_snapshot, case.issue_board)
```

**Evidence Ledger** 字段：`entry_id, claim, submitted_by, evidence_source_id, exact_span, verification_status, related_issue_ids, round_index, accepted_by_judge`。工具返回的新来源先标为未经核实，不能当作已证实事实。若双方引用同一不可靠来源，也不能算双重验证。

**裁判输出**：`upheld`（维持）、`partially_revised`（部分调整）、`recommend_revoke`（建议撤销）、`insufficient_evidence`（无法裁定/请求补证）；给出逐争点理由、实际证据与适用限制。结果追加为 `Judgment`，不覆盖旧审核记录；用户或主审核复核流程确认后才改变面向用户的最新风险状态。

**戏剧体验**：三角色头像、时间线、Objection、传唤证人、提交新证据、请求法官裁决；UI 只展示可审核的论据、引用和公开发言，不展示或声称获得模型隐藏思维链。

### 5\.4 最低限度抗偏差措施

- 控辩都必须引用同一个可追溯规则库，但可主动检索新证据；观点不是证据。

- 每轮尝试处理一个尚未解决争点，禁止无意义复述。

- 独立裁判不继承辩方/控方设定的角色立场，不把口才/轮数当置信度。

- 对关键结论作一次基于原文的重新核验；用户可看到理由、证据与剩余不确定性。

## 消费者陪审团：企业 Persona 驱动，而非凭空生成人群

### 6\.1 触发机制与范围

消费者陪审团**不是常驻 Agent**；仅在用户主动启用时运行。企业已有 Buyer Persona/客群研究文档优先作为基础。允许只有一个 Persona，绝不自动声称它代表整个市场。没有画像时用户可以选择“探索性虚拟画像”，并以明显标签提示其不具代表性。

### 6\.2 Persona Compiler

读取 PDF/DOCX/文本里的目标客户描述，生成结构化 `PersonaProfile`：购买动机、JTBD、关注因素、已知价格敏感度、已有渠道习惯、品牌态度、证据出处。每个字段标记 `grounded`（文档明确）、`inferred`（模型推断）或 `unknown`，保留原文 `source_span`。允许企业用户编辑/确认，不把未知属性硬填成“典型消费者”。避免未经授权推断种族、政治倾向、健康状况等敏感信息。

### 6\.3 Marketing Behavior Model \+ Scenario Planner

- **STP**：尊重企业已有的细分/目标市场和定位，不任意生成额外“市场份额”。

- **JTBD**：确定消费者要完成的任务、核心购买动机、替代选择。

- **ELM**：按观看情境与动机/能力设置较深或较浅的信息加工条件；不是按人群身份机械分配思考能力。

- **PKM**：测试消费者可能如何识别夸张措辞、商业意图或信任线索。

一份 Persona 可以在**不同情境**下出现多个模拟实例（刷短视频、认真比价、线下看包装）；或在同一情境多次独立抽样。二者都不等于创建了多个真实细分市场。Scenario Planner 输出 `persona_id, context, attention_conditions, purchase_job, theoretical_basis, assumptions`，并显式注明哪些条件是实验假设。

### 6\.4 Blind Exposure 与独立回答

模拟消费者第一次看到的是**原始广告及最小购买情境**，不能提前看到原审核的“违规”标签、控辩论点或其他陪审员的票数，以免造成诱导与信息污染。隔离上下文运行每次 LLM 调用，使用相同的问卷维度：

1. 用自己的话复述广告承诺；

2. 哪个信息最受关注/最容易误解；

3. 哪些事实需要核实；

4. 信任或怀疑的理由；

5. 购买考虑受到何种影响（不是预测真实转化率）；

6. 不确定性与未理解内容。

聚合结果展示**具体意见、分歧、潜在误读类型、跨情境的稳定性**，可辅助营销人员决定应进行哪种真人用户测试。只能写“6 次模拟中有 4 次提出某疑虑”，不可写“67% 目标消费者反对”。不宜将多次模型采样视为独立统计样本。

### 6\.5 消费者证人与 A/B 测试

庭审可“传唤”某位已盲测的模拟消费者作为证人：**冻结其初次作答**，后续质询单独保存，避免对方律师诱导它改写先前记忆。证词是模拟情景材料，不自动成为法律事实。

对修改前 A、修改后 B 的广告测试，应保持 Persona、情境、提问与模型版本可比；会话相互隔离，必要时随机化/平衡 A/B 呈现顺序；报告定性差异而非承诺转化率提升。条件允许时再用真实用户小样本调查校准。

## 前端交互与页面划分

1. **Project Setup**：上传广告、国家/平台/品类、可选企业资料。

2. **Review Workspace**：左侧原始素材（文字坐标红框/黄框）；右侧按风险项排列，点击联动定位、看法规来源与产品证据、采纳局部改写；顶部显示真实任务阶段和版本信息。

3. **Courtroom**：中央控方/律师发言时间线；左侧争议与证据台账；右侧用户发言、新证据和预算控制；裁判出场后显示四类结论及对应依据。

4. **Consumer Jury**：上传 Persona、确认抽取字段、配置情境/次数、查看首次理解与分歧；支持作为证人送入庭审。

5. **Comparison \& Export**：V1/V2 风险变化、来源变化、消费者模拟差异、人工待办和报告导出。

\*\*用户可见的“正在审核”\*\*应来自真实后端事件 `asset_parsed / claims_extracted / retrieval_completed / risk_validated / rewrite_completed / court_round_finished`，不伪造模型内部思维过程。

## API 与服务边界（首版建议）

所有长任务均返回任务 ID 和服务端状态，而不是在单次 HTTP 请求里一直阻塞。用幂等键防止刷新页面/重试重复扣费；对用户输入和角色工具调用加权限与速率限制。

## 代码目录与模块边界

```Plain Text
marketing-court/
├── README.md
├── .env.example
├── pyproject.toml
├── backend/
│   ├── app/main.py                 # FastAPI 入口
│   ├── app/api/                    # 路由/请求模型
│   ├── app/core/                   # 配置、日志、任务事件、模型适配器
│   ├── app/models/                 # Pydantic + 持久化数据模型
│   ├── app/workflows/review.py     # 固定审核流程
│   ├── app/services/parsing.py     # PDF/DOCX/image 解析
│   ├── app/services/ocr.py         # OCR 与坐标
│   ├── app/services/claims.py      # 宣称提取及 Anchor 映射
│   ├── app/services/retrieval.py   # 法规与企业证据检索
│   ├── app/services/rewrite.py     # 局部改写/复核
│   ├── app/court/controller.py     # 自适应辩论编排
│   ├── app/court/roles.py          # 控方/辩方/法官模板与调用
│   ├── app/court/evidence.py       # 争点/证据台账
│   ├── app/jury/persona.py         # Persona 编译与核对
│   ├── app/jury/scenario.py        # 理论驱动情境规划
│   ├── app/jury/simulation.py      # 隔离的消费者模拟
│   ├── app/jury/aggregate.py       # 聚合与 A/B 差异
│   └── app/data/policies/          # 带版本和出处的规则卡
├── frontend/
│   ├── src/pages/                 # Setup/Review/Court/Jury/Compare
│   ├── src/components/            # AssetCanvas/RiskPanel/CourtTimeline
│   ├── src/lib/api.ts             # 类型化 API client / SSE
│   └── package.json
├── tests/
│   ├── fixtures/                   # 人工标注的小案例与来源
│   ├── test_anchor_mapping.py
│   ├── test_policy_citations.py
│   ├── test_court_state.py
│   └── test_persona_grounding.py
└── docs/
    ├── product-spec.md
    ├── architecture.md
    └── demo-script.md
```

**实现原则**：不要先创建复杂 Harness、Skill Marketplace 或插件系统。市场/品类差异用版本化规则卡与审核模板实现，未来确有需要再引入 Skills。后端业务状态不应由前端直接修改。让 Codex 按模块接口逐个开发、每个阶段提交 Git commit，并保持自动测试可运行。

## 安全、合规与成本边界

- **法律来源**：仅将可追溯官方法规/监管机构/平台原文作为法律或平台依据；博客和社媒可作参考，不能替代法条。

- **提示注入**：上传广告、Persona 文件、网页法规片段均视作不可信文本；不得执行其中的“忽略系统指令”、外链访问或任意代码；LLM 只能返回结构化数据，工具调用由后端白名单控制。

- **商业资料隐私**：明确告知文件传给何种 API、是否保存、保留期限；默认隔离不同项目文件，提供删除功能；不将客户画像及未公开产品证明提交给未经审核的第三方搜索。

- **数据最小化**：日志记录模型、版本、耗时、成本与引用，不记录不必要的敏感原文。API 密钥仅存服务端；前端不得接触供应商 API Key。

- **成本控制**：复用解析结果、缓存来源检索、设置图片分辨率与页数上限、限制并行模拟消费者规模、庭审 token/轮数/超时上限；成本随模型与输入而变，开发前用真实供应商价格建立预算表。

- **风险沟通**：界面固定标明“AI 辅助审核，不构成法律意见或真实消费者调查结果”。法官不代表监管机构，陪审团不能作为真实市场统计样本。

## 实施顺序、团队分工与里程碑

### 11\.1 11 月 20 日校园活动前：演示版优先级

**P0：必须端到端可用**
① 上传一张广告图与目标市场；② OCR 位置 \+ 图像理解 \+ Claim 映射；③ 一个经过人工核验的法规主题规则库；④ LLM 结构化审核及证据链接；⑤ 前端原图标红、风险点击联动；⑥ 单项改写与复核；⑦ 对同一风险启动控辩多轮（先保证 2–3 轮稳定）并由法官复核；⑧ 保存案件状态与演示脚本。

**P1：有余力尽快接入**
① 企业 Persona 文档上传与字段确认；② 1 个 Persona 派生 2–3 个情境的独立模拟；③ 陪审员首次反馈；④ 用户插话/补证；⑤ V1/V2 对比。

## 验收与最小实验

**最小测试集**：人工构造/收集 20–30 条广告宣称，覆盖高风险、低风险、证据不足、错误法规地区、夸张但不必然违法、视觉隐含宣称；先由人工核对法规出处及可接受答案范围。不要只用同一模型生成并给自己打标签。

**两个特别有用的对照实验**：

A\. 相同素材和规则：`Single Review` vs `Review + Self-check` vs `Review + 3-round Debate`，比较人工判定的错误纠正情况、引用真实性与成本，而不比较模型自称的“置信度”。

B\. 相同 Persona 和广告：`Raw Persona` vs `Persona + JTBD/ELM/PKM Scenario`，比较模拟回应的具体性、可解释性和跨重复稳定性；如能找到真人调研材料，再评估哪种更接近真实反馈。

## 关键风险与决策记录

1. **法规差异复杂**：首个演示只覆盖一个明确案例与有限规则，不能把“欧盟整体”说成所有国家所有品类均适用。

2. **多 Agent 辩论可能强化偏误**：裁判须独立核证，辩论轮数依成本与证据增量控制。

3. **消费者模拟不等于购买行为预测**：尤其不能从几名虚拟陪审员投票推出市场份额。

4. **OCR 准确率不等于语义判断准确率**：两个链路单独测试，无法映射时降级为文本列表。

5. **真正替换图片文本比标注难**：首版实现 overlay 和文案预览，不承诺原画可编辑导出。

6. **审核不是合规保证**：每个风险结论需要说明是否缺少权威规则或产品事实。

7. **不要为技术名词增加复杂度**：RAG、Skills、Agents 必须各自解决真实功能问题；可确定的步骤交给 Workflow。

## 参考资料与核查起点

以下链接为架构和规则核查起点；具体政策实施前必须再次核对最新原文、适用地区及时间。

- 欧盟 Directive \(EU\) 2024/825 正式文本：[https://eur\-lex\.europa\.eu/eli/dir/2024/825](https://eur-lex.europa.eu/eli/dir/2024/825)。其中列举了 `eco-friendly` 等泛化环保宣称，相关国内转化措施自 2026\-09\-27 起适用。

- OpenAI Structured Outputs：[https://developers\.openai\.com/api/docs/guides/structured\-outputs?api\-mode=responses](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)；Responses API：[https://developers\.openai\.com/api/reference/resources/responses/methods/create](https://developers.openai.com/api/reference/resources/responses/methods/create)。

- PaddleOCR OCR 输出文本与坐标：[https://www\.paddleocr\.ai/v3\.0\.0/en/version3\.x/pipeline\_usage/OCR\.html](https://www.paddleocr.ai/v3.0.0/en/version3.x/pipeline_usage/OCR.html)。

- Petty \& Cacioppo, Elaboration Likelihood Model：[https://doi\.org/10\.1016/S0065\-2601\(08\)60214\-2](https://doi.org/10.1016/S0065-2601%2808%2960214-2)。

- Friestad \& Wright \(1994\), Persuasion Knowledge Model：[https://academic\.oup\.com/jcr/article\-abstract/21/1/1/1853712](https://academic.oup.com/jcr/article-abstract/21/1/1/1853712)。

- Harvard Business School, Jobs to Be Done：[https://online\.hbs\.edu/blog/post/jobs\-to\-be\-done\-examples](https://online.hbs.edu/blog/post/jobs-to-be-done-examples)。

- NeurIPS 2025, Multi\-Agent Debate with Adaptive Stability Detection：[https://papers\.neurips\.cc/paper\_files/paper/2025/hash/42475c537936b2394b5015e871765056\-Abstract\-Conference\.html](https://papers.neurips.cc/paper_files/paper/2025/hash/42475c537936b2394b5015e871765056-Abstract-Conference.html)。

- NeurIPS 2025, LLM Generated Persona is a Promise with a Catch：[https://proceedings\.neurips\.cc/paper\_files/paper/2025/hash/5fc150b75e8b509735564de16bc3527b\-Abstract\-Position\_Paper\_Track\.html](https://proceedings.neurips.cc/paper_files/paper/2025/hash/5fc150b75e8b509735564de16bc3527b-Abstract-Position_Paper_Track.html)。

---

**定版建议**：第一阶段交付一个有证据、有坐标、有可复核状态的审核 Workflow；第二阶段用真正自主多轮的模拟法庭建立互动记忆点；第三阶段通过企业 Persona 驱动的可选消费者陪审团增强营销洞察。模块互不假设对方存在，后续可以独立演进。

