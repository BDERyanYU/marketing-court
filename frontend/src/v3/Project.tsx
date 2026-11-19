import { useState } from 'react'
import AssetCanvas from '../components/AssetCanvas'
import { resourceUrl } from '../lib/api'
import { marketName, categoryName } from '../lib/project-options'
import type { Context, Detail, Persona, Review } from './types'
import { Badge, channels, Conclusions, date, PersonaSummary, states } from './common'

export default function ProjectPage({
  detail,
  reviewId,
  selectReview,
  personas,
  busy,
  saveContext,
  upload,
  derive,
  meeting,
  openMeeting,
  rewrite,
  archive,
  saveDecision,
}: {
  detail: Detail
  reviewId: string
  selectReview: (id: string) => void
  personas: Persona[]
  busy: boolean
  saveContext: (value: Context) => void
  upload: () => void
  derive: () => void
  meeting: (ids: string[]) => void
  openMeeting: (id: string) => void
  rewrite: (review: Review, riskId: string) => void
  archive: () => void
  saveDecision: (trigger: string) => void
}) {
  const [stage, setStage] = useState(1)
  const [risk, setRisk] = useState('')
  const [reason, setReason] = useState(detail.decisions?.[reviewId] ?? '')
  const [selectedIssues, setSelectedIssues] = useState<string[]>([])
  const [context, setContext] = useState(detail.context)
  const review = detail.reviews.find((r) => r.review_id === reviewId) ?? detail.reviews[0]
  const asset =
    detail.assets.find((a) => a.asset_version_id === review?.asset_version_id) ?? detail.assets[0]
  const issues = review
    ? [
        ...review.risks.map((r) => ({ id: r.risk_id, quote: r.claim_quote })),
        ...(review.risks.length
          ? []
          : (review.claims ?? []).map((c) => ({ id: c.claim_id, quote: c.claim_text }))),
      ]
    : []
  if (review && issues.length === 0)
    issues.push({ id: `report:${review.review_id}`, quote: '复核报告的覆盖范围与证据边界' })
  const toggle = (id: string) =>
    setSelectedIssues(
      selectedIssues.includes(id)
        ? selectedIssues.filter((i) => i !== id)
        : [...selectedIssues, id],
    )
  const startMeeting = () =>
    meeting(selectedIssues.length ? selectedIssues : issues.map((i) => i.id))
  return (
    <>
      <div className="project-heading">
        <div>
          <div className="eyebrow">出海营销项目</div>
          <h1>{detail.project.name}</h1>
          <p>
            {marketName(detail.project.market)} <span>/</span> {channels[detail.project.channel]}{' '}
            <span>/</span> {categoryName(detail.project.product_category)}
          </p>
        </div>
        <Badge tone={detail.status}>{states[detail.status]}</Badge>
      </div>
      <nav className="stage-bar" aria-label="项目阶段">
        {['素材与用户画像', '审核报告', '圆桌会议', '结论与导出'].map((label, i) => (
          <button
            key={label}
            onClick={() => setStage(i)}
            aria-current={stage === i ? 'step' : undefined}
          >
            <span>{i + 1}</span>
            {label}
          </button>
        ))}
      </nav>
      {detail.tasks
        .filter((t) => ['failed', 'interrupted'].includes(t.status))
        .slice(0, 1)
        .map((t) => (
          <p className="notice" key={t.task_id}>
            上次任务未完成：{t.error}。可以在上方任务进度中重试，或添加新版本。
          </p>
        ))}
      {stage < 2 && (
        <div className="project-columns">
          <section className="surface material-column">
            <div className="section-title">
              <h2>项目素材</h2>
              <button className="text-button" onClick={upload} disabled={busy}>
                添加版本
              </button>
            </div>
            <label className="field">
              审核版本
              <select
                aria-label="审核版本"
                value={review?.review_id ?? ''}
                onChange={(e) => {
                  selectReview(e.target.value)
                  setSelectedIssues([])
                  setRisk('')
                  setReason('')
                }}
              >
                {detail.reviews.length ? (
                  detail.reviews.map((r, i) => (
                    <option key={r.review_id} value={r.review_id}>
                      版本 {detail.reviews.length - i} · {date(r.created_at)}
                      {r.mode === 'demo' ? ' · 预设' : ''}
                    </option>
                  ))
                ) : (
                  <option value="">尚无审核报告</option>
                )}
              </select>
            </label>
            {asset ? (
              <>
                <div className="material-meta">
                  <Badge>
                    {asset.kind === 'text'
                      ? '广告文案'
                      : asset.kind === 'copy'
                        ? '文案修改版'
                        : asset.text
                          ? '图片＋文案'
                          : '广告图片'}
                  </Badge>
                  <small>
                    {(asset as typeof asset & { language?: string }).language ?? '英语'}
                  </small>
                </div>
                <AssetCanvas
                  asset={asset}
                  review={review ?? null}
                  selectedRisk={risk}
                  onSelect={setRisk}
                />
                {asset.kind === 'image' && asset.text && (
                  <section className="submitted-copy">
                    <h3>同时提交的文案</h3>
                    <AssetCanvas
                      asset={{ ...asset, kind: 'text' }}
                      review={
                        review
                          ? { ...review, original_text: review.supplied_text ?? asset.text }
                          : null
                      }
                      selectedRisk={risk}
                      onSelect={setRisk}
                    />
                  </section>
                )}
                <small className="material-filename">{asset.original_filename}</small>
              </>
            ) : (
              <div className="empty">
                <h3>把第一份素材放进项目</h3>
                <p>图片、文案、落地页截图或二者一起提交。</p>
                <button onClick={upload}>添加素材</button>
              </div>
            )}
            <p className="fine-print">
              图片检查当前只覆盖识别出的文字；多语言识别效果取决于已安装的 OCR 模型。
            </p>
          </section>
          <section className="surface report-column">
            <div className="section-title">
              <h2>审核报告</h2>
              {review && (
                <Badge
                  tone={
                    review.coverage_status === 'unsupported'
                      ? ''
                      : review.risks.length
                        ? 'risk'
                        : 'ok'
                  }
                >
                  {review.coverage_status === 'unsupported'
                    ? '未作风险判定'
                    : `${review.risks.length} 项待核查`}
                </Badge>
              )}
            </div>
            {review ? (
              <>
                {review.mode === 'demo' && (
                  <p className="notice">
                    预设演示报告；
                    {review.example
                      ? '文案来自 GreenLint 案例包。'
                      : '图片、文字与坐标为人工预设。'}
                  </p>
                )}
                <div className="report-dimensions">
                  <div>
                    <small>环保文字宣称</small>
                    <strong>
                      {review.coverage_status === 'unsupported'
                        ? '规则待接入'
                        : review.risks.length
                          ? '需要复核'
                          : '未识别到待核查项'}
                    </strong>
                  </div>
                  <div>
                    <small>画像匹配</small>
                    <strong>
                      {review.audience_fit
                        ? { aligned: '方向匹配', mixed: '部分匹配', unknown: '信息不足' }[
                            review.audience_fit.status
                          ]
                        : '尚未评估'}
                    </strong>
                  </div>
                  <div>
                    <small>视觉 / 渠道专项</small>
                    <strong>尚未覆盖</strong>
                  </div>
                </div>
                <p className="fine-print">当前提供风险与定性意见，未建立经过校准的维度评分。</p>
                {review.audience_fit && (
                  <div className="fit-note">
                    <strong>素材与画像匹配意见</strong>
                    <p>{review.audience_fit.reason}</p>
                    {review.audience_fit.suggestions.map((s) => (
                      <p key={s}>· {s}</p>
                    ))}
                  </div>
                )}
                {review.risks.map((r, index) => (
                  <article
                    className={`issue ${risk === r.risk_id ? 'selected' : ''}`}
                    key={r.risk_id}
                  >
                    <div className="issue-top">
                      <button className="text-button" onClick={() => setRisk(r.risk_id)}>
                        问题 {index + 1} ·{' '}
                        {r.input_origin === 'text' || asset?.kind === 'text'
                          ? '文案片段'
                          : r.location_status === 'located'
                            ? '已定位原图'
                            : '定位待确认'}
                      </button>
                      <Badge tone={r.severity}>
                        {r.severity === 'high'
                          ? '高风险'
                          : r.severity === 'medium'
                            ? '中风险'
                            : '低风险'}
                      </Badge>
                    </div>
                    <blockquote>{r.claim_quote}</blockquote>
                    <p>{r.reason}</p>
                    <details>
                      <summary>依据与待补材料</summary>
                      {review.sources
                        .filter((s) => r.source_ids.includes(s.source_id))
                        .map((s) => (
                          <div className="source" key={s.source_id}>
                            <a href={s.url} target="_blank" rel="noreferrer">
                              {s.source_id} · {s.title}
                            </a>
                            <q>{s.excerpt}</q>
                            <small>核查 {s.checked_at}</small>
                          </div>
                        ))}
                      {r.evidence_gaps.map((g) => (
                        <p key={g}>待补：{g}</p>
                      ))}
                    </details>
                    <div className="issue-actions">
                      <button
                        className="secondary"
                        onClick={() => rewrite(review, r.risk_id)}
                        disabled={busy}
                      >
                        谨慎改写与复核
                      </button>
                      <label>
                        <input
                          type="checkbox"
                          checked={selectedIssues.includes(r.risk_id)}
                          onChange={() => toggle(r.risk_id)}
                        />
                        引用到圆桌
                      </label>
                    </div>
                  </article>
                ))}
                {!review.risks.length && (
                  <div className="no-risk">
                    <h3>
                      {review.coverage_status === 'unsupported'
                        ? '该市场规则尚未接入'
                        : review.example?.polarity === 'positive'
                          ? '正面对照：未发现明显风险'
                          : '未识别到本主题待核查项'}
                    </h3>
                    <p>
                      {review.coverage_status === 'unsupported'
                        ? '仅提取文字和宣称，不能据此判断风险。'
                        : '不代表品牌、产品或素材已获投放批准。'}
                    </p>
                    {issues.map((i) => (
                      <label className="claim-choice" key={i.id}>
                        <input
                          type="checkbox"
                          checked={selectedIssues.includes(i.id)}
                          onChange={() => toggle(i.id)}
                        />
                        {i.quote}
                      </label>
                    ))}
                  </div>
                )}
                {detail.addenda
                  .filter((a) => a.review_id === review.review_id)
                  .map((a) => (
                    <details className="report-addendum" key={a.addendum_id}>
                      <summary>
                        <strong>圆桌回写结论</strong>
                        <span>{date(a.created_at)}</span>
                        <Badge tone="ok">已追加保存</Badge>
                      </summary>
                      <Conclusions value={a.conclusion} />
                      <button className="text-button" onClick={() => openMeeting(a.meeting_id)}>
                        查看会议来源
                      </button>
                    </details>
                  ))}
                <section className="decision-box">
                  <h3>这份结果是否解决了问题？</h3>
                  <div className="decision-options">
                    {[
                      ['unsatisfied', '不满意'],
                      ['high_risk', '风险较高'],
                      ['disputed', '有争议'],
                    ].map(([value, label]) => (
                      <label key={value}>
                        <input
                          type="radio"
                          name="decision"
                          value={value}
                          checked={reason === value}
                          onChange={() => {
                            setReason(value)
                            saveDecision(value)
                          }}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                  {reason && (
                    <button disabled={busy || !issues.length} onClick={startMeeting}>
                      发起圆桌会议
                    </button>
                  )}
                  {!issues.length && (
                    <p className="fine-print">
                      报告暂无可讨论的风险或宣称，请添加明确的广告文字后重新审核。
                    </p>
                  )}
                </section>
                <details className="boundaries">
                  <summary>审核范围与版本</summary>
                  {review.limitations.map((s) => (
                    <p key={s}>{s}</p>
                  ))}
                  <small>
                    规则 {review.rule_pack_version} / {review.model}
                  </small>
                </details>
              </>
            ) : (
              <div className="empty">
                <h3>还没有审核报告</h3>
                <p>添加素材后，报告会与项目版本一起保存。</p>
                <button onClick={upload}>提交审核</button>
              </div>
            )}
          </section>
          <aside className="surface context-column">
            <div className="section-title">
              <h2>用户画像与市场</h2>
            </div>
            <h3>当前项目画像</h3>
            {detail.personas.length ? (
              detail.personas.map((p) => <PersonaSummary key={p.persona_id} persona={p} />)
            ) : (
              <p className="muted">选择或派生目标画像，为下一轮审核与圆桌提供受众上下文。</p>
            )}
            <button className="secondary" onClick={derive} disabled={busy || !review}>
              从当前素材派生画像
            </button>
            <label className="field">
              选择画像版本
              <select
                multiple
                aria-label="项目用户画像"
                value={context.persona_ids}
                onChange={(e) =>
                  setContext({
                    ...context,
                    persona_ids: Array.from(e.target.selectedOptions, (o) => o.value),
                  })
                }
              >
                {personas.map((p) => (
                  <option key={p.persona_id} value={p.persona_id}>
                    {p.name} · v{p.version}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              素材语言
              <input
                value={context.language}
                onChange={(e) => setContext({ ...context, language: e.target.value })}
                maxLength={80}
              />
            </label>
            <label className="field">
              品牌 / 法务提示
              <textarea
                rows={3}
                value={context.brand_notes}
                onChange={(e) => setContext({ ...context, brand_notes: e.target.value })}
                maxLength={1600}
              />
            </label>
            <label className="field">
              市场、文化与渠道备注
              <textarea
                rows={3}
                value={context.market_notes}
                onChange={(e) => setContext({ ...context, market_notes: e.target.value })}
                maxLength={1600}
                placeholder="记录待验证的市场背景与渠道要求"
              />
            </label>
            <button
              className="secondary wide"
              disabled={busy || context.persona_ids.length > 6}
              onClick={() => saveContext(context)}
            >
              保存上下文
            </button>
            <p className="fine-print">
              保存后用于下一次审核；既有报告与会议保留当时快照。最多选择 6 个画像版本。
            </p>
            {review?.audience_context?.personas?.length ? (
              <details>
                <summary>本次审核采用的画像</summary>
                {review.audience_context.personas.map((p) => (
                  <PersonaSummary key={p.persona_id} persona={p} />
                ))}
              </details>
            ) : null}
            <div className="scope-note">
              <h3>规则覆盖</h3>
              <p>
                {detail.project.market === 'GB'
                  ? '英国 CMA 通用环保文字指引；专项品类、视觉和渠道规定需另外核查。'
                  : '该市场规则待接入，不套用英国审核结论。'}
              </p>
            </div>
          </aside>
        </div>
      )}
      {stage === 2 && (
        <section className="surface">
          <div className="section-title">
            <h2>项目圆桌会议</h2>
            <button className="secondary" onClick={() => setStage(1)}>
              返回报告选择议题
            </button>
          </div>
          {detail.meetings.length ? (
            detail.meetings.map((m) => (
              <button
                key={m.meeting_id}
                className="record-row"
                onClick={() => openMeeting(m.meeting_id)}
              >
                <div>
                  <strong>{m.title}</strong>
                  <small>
                    {date(m.created_at)} · {m.roles.length} 位角色 · {m.turns.length} 次发言
                  </small>
                </div>
                <Badge>{m.status === 'completed' ? '有结论' : '进行中'}</Badge>
              </button>
            ))
          ) : (
            <div className="empty">
              <h3>从审核结果开始讨论</h3>
              <p>先选择具体问题，再邀请不同角色合议。</p>
            </div>
          )}
        </section>
      )}
      {stage === 3 && (
        <section className="surface">
          <h2>结论与导出</h2>
          {detail.addenda.length ? (
            detail.addenda.map((a) => (
              <article className="report-addendum" key={a.addendum_id}>
                <h3>会议结论 · {date(a.created_at)}</h3>
                <Conclusions value={a.conclusion} />
                <button className="secondary" onClick={() => openMeeting(a.meeting_id)}>
                  打开原会议
                </button>
              </article>
            ))
          ) : (
            <p className="muted">圆桌结论回写后会在此汇总。你也可以直接导出当前报告。</p>
          )}
        </section>
      )}
      <div className="project-actionbar">
        <span>
          {review ? `报告 ${date(review.created_at)}` : '素材 → 用户画像 → 审核 → 圆桌 → 结论'}
        </span>
        <div>
          {review && (
            <a
              className="secondary button"
              href={resourceUrl(`/api/reviews/${review.review_id}/report`)}
              download
            >
              导出报告
            </a>
          )}
          <button className="secondary" onClick={upload} disabled={busy}>
            修改后复审
          </button>
          <button className="secondary" onClick={archive} disabled={busy || !review}>
            {detail.context.archived ? '重新打开项目' : '满意并归档'}
          </button>
          {reason && issues.length > 0 && (
            <button disabled={busy} onClick={startMeeting}>
              发起圆桌会议
            </button>
          )}
        </div>
      </div>
    </>
  )
}
