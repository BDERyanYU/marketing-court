import type { CourtCase } from '../lib/types'
import Icon from '../components/Icon'

const dispositions: Record<string, string> = {
  upheld: '维持风险意见',
  partially_revised: '部分调整意见',
  recommend_revoke: '建议撤销风险项',
  insufficient_evidence: '证据不足，建议补证',
}
const positions: Record<string, string> = {
  maintain: '维持主张',
  challenge: '提出质疑',
  narrow: '收窄主张',
  concede: '认可论点',
  withdraw: '撤回主张',
  request_evidence: '请求补证',
}
const steps: Record<string, string> = {
  prosecution_1: '第一轮 · 控方',
  defense_1: '第一轮 · 辩方',
  prosecution_2: '第二轮 · 控方',
  defense_2: '第二轮 · 辩方',
  judgment: '独立法官复核',
}

export default function Court({
  court,
  busy,
  auto,
  onAuto,
  onAdvance,
  onBack,
}: {
  court: CourtCase | null
  busy: boolean
  auto: boolean
  onAuto: () => void
  onAdvance: () => void
  onBack: () => void
}) {
  if (!court)
    return (
      <div className="empty-state">
        <span className="empty-icon">
          <Icon name="scales" size={34} />
        </span>
        <h1>让争议回到证据。</h1>
        <p>从审核工作台选择一条风险，提出异议后开启庭审。</p>
        <button className="primary" onClick={onBack}>
          返回审核工作台 <Icon name="arrow" size={17} />
        </button>
      </div>
    )
  return (
    <>
      <div className="page-heading compact">
        <div>
          <h1>观点可以交锋，证据必须可查。</h1>
          <p className="intro">两轮控辩 · 独立法官复核 · 案件进度自动保存</p>
        </div>
        <button className="secondary" onClick={onBack}>
          <Icon name="back" size={17} />
          返回审核
        </button>
      </div>
      <div className="court-grid">
        <aside className="panel case-file">
          <div className="case-heading">
            <span className="title-icon">
              <Icon name="folder" />
            </span>
            <strong>案件档案</strong>
          </div>
          <span className="small-tag">
            {court.mode === 'demo' ? '固定发言演示' : '实时模型发言'}
          </span>
          <h2>争议宣称</h2>
          <blockquote>{court.snapshot.claim_quote}</blockquote>
          <p className="muted">
            {court.snapshot.market === 'EU' ? '欧盟' : '英国'} · 产品证明未提供
          </p>
          <h3>冻结的规则与依据</h3>
          {court.snapshot.citations.map((s) => (
            <div className="source" key={s.source_id}>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.source_id} · 查看原文 ↗
              </a>
              <q>{s.excerpt}</q>
            </div>
          ))}
          <small>
            案件 {court.case_id.slice(0, 8)}
            <br />
            模型 {court.model}
            <br />
            法官意见将追加保存，原审核记录保留。
          </small>
        </aside>
        <section className="court-timeline">
          <ol className="court-progress" aria-label="庭审进度">
            {Object.entries(steps).map(([key, label], index) => {
              const completed =
                key === 'judgment'
                  ? Boolean(court.judgment)
                  : court.turns.some((turn) => turn.step === key)
              return (
                <li
                  key={key}
                  className={completed ? 'done' : court.next_step === key ? 'current' : ''}
                  aria-current={court.next_step === key ? 'step' : undefined}
                >
                  <span>{completed ? <Icon name="check" size={14} /> : index + 1}</span>
                  <small>{label.replace(' · ', '')}</small>
                </li>
              )
            })}
          </ol>
          <div className="court-controls">
            <div>
              <span className="status-dot online" />
              <strong>
                {court.next_step ? `下一步：${steps[court.next_step]}` : '庭审已完成'}
              </strong>
              <p>
                {busy
                  ? '正在等待当前角色返回，已保存发言不会丢失。'
                  : `${court.turns.length} / 4 次控辩发言已保存`}
              </p>
            </div>
            {court.next_step && (
              <div className="control-buttons">
                <button className="secondary" disabled={!auto && busy} onClick={onAuto}>
                  {auto ? '暂停后续发言' : '自动完成庭审'}
                </button>
                <button className="primary" disabled={busy || auto} onClick={onAdvance}>
                  {busy ? '生成中…' : '推进下一步'}
                  {!busy && <Icon name="arrow" size={16} />}
                </button>
              </div>
            )}
          </div>
          {court.turns.length === 0 && (
            <div className="timeline-empty">
              <span>
                <Icon name="scales" size={39} />
              </span>
              <h3>案卷已建立</h3>
              <p>选择逐步推进，或自动完成两轮控辩与裁判。</p>
            </div>
          )}
          {court.turns.map((turn) => (
            <article className={`turn ${turn.role}`} key={turn.step}>
              <div className="role-avatar">{turn.role === 'prosecutor' ? '控' : '辩'}</div>
              <div className="turn-body">
                <div className="turn-header">
                  <h3>{turn.role === 'prosecutor' ? '控方' : '辩方律师'}</h3>
                  <span>
                    第 {turn.round} 轮 · {positions[turn.position]}
                  </span>
                </div>
                <p>{turn.argument}</p>
                <div className="citation-tags">
                  {turn.source_ids.map((id) => (
                    <a
                      key={id}
                      href={court.snapshot.citations.find((s) => s.source_id === id)?.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      依据 {id} ↗
                    </a>
                  ))}
                </div>
                {turn.evidence_requested.length > 0 && (
                  <div className="requested">待补证：{turn.evidence_requested.join('；')}</div>
                )}
              </div>
            </article>
          ))}
          {court.judgment && (
            <article className="judgment">
              <div className="judgment-label">
                <Icon name="scales" size={19} />
                <span>独立法官复核</span>
                <span className="judgment-saved">
                  <Icon name="check" size={14} />
                  已保存
                </span>
              </div>
              <h2>{dispositions[court.judgment.disposition]}</h2>
              <p>{court.judgment.reason}</p>
              <div className="citation-tags">
                {court.judgment.source_ids.map((id) => (
                  <a
                    key={id}
                    href={court.snapshot.citations.find((s) => s.source_id === id)?.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    依据 {id} ↗
                  </a>
                ))}
              </div>
              {court.judgment.evidence_requested.length > 0 && (
                <div className="requested">
                  待补材料：{court.judgment.evidence_requested.join('；')}
                </div>
              )}
              <small>这是非正式风险复核建议，投放决定需人工确认。</small>
            </article>
          )}
        </section>
      </div>
    </>
  )
}
