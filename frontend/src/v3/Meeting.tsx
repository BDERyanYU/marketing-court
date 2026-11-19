import { useState } from 'react'
import { marketName } from '../lib/project-options'
import { resourceUrl } from '../lib/api'
import type { Meeting } from './types'
import {
  Badge,
  channels,
  Conclusions,
  date,
  downloadJson,
  goals,
  PersonaSummary,
  roleNames,
  votes,
} from './common'

export default function MeetingPage({
  value,
  busy,
  advance,
  writeback,
  recheck,
  back,
}: {
  value: Meeting
  busy: boolean
  advance: (instruction: string) => Promise<void>
  writeback: () => void
  recheck: (text: string) => void
  back: () => void
}) {
  const [instruction, setInstruction] = useState('')
  const [copy, setCopy] = useState(value.conclusion?.revised_copy ?? '')
  const [showRecheck, setShowRecheck] = useState(false)
  const next =
    value.turns.length < value.roles.length * 2
      ? roleNames[value.roles[value.turns.length % value.roles.length]]
      : '主持人归纳结论'
  const review = value.review_snapshot
  const issues = [
    ...review.risks.map((r) => ({ id: r.risk_id, quote: r.claim_quote })),
    ...(review.claims ?? []).map((c) => ({ id: c.claim_id, quote: c.claim_text })),
  ].filter((i) => value.issue_ids.includes(i.id))
  if (value.issue_ids.includes(`report:${review.review_id}`))
    issues.push({ id: `report:${review.review_id}`, quote: '复核报告的覆盖范围与证据边界' })
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">圆桌会议 · {value.project_name}</div>
          <h1>{value.title}</h1>
          <p>
            {goals[value.goal]} <span>/</span> {value.roles.length} 位角色，两轮讨论与主持人归纳
          </p>
        </div>
        <button className="secondary" onClick={back}>
          返回项目报告
        </button>
      </div>
      {value.mode === 'demo' && (
        <p className="notice">固定演示会议：发言与结论为预设示例，不代表真实模型讨论。</p>
      )}
      <div className="meeting-columns">
        <aside className="surface meeting-context">
          <h2>项目上下文</h2>
          <p className="context-project-name">{value.project_name}</p>
          <div className="metadata">
            <span>{value.market ? marketName(value.market) : '未带入市场背景'}</span>
            <span>{channels[value.channel]}</span>
          </div>
          {review.anchors.length > 0 && (
            <img
              className="meeting-thumb"
              src={resourceUrl(`/api/assets/${review.asset_version_id}/image`)}
              alt="会议引用的广告素材"
            />
          )}
          <h3>本次议题</h3>
          <ul className="issue-quotes">
            {issues.map((i) => (
              <li key={i.id}>{i.quote}</li>
            ))}
          </ul>
          <details>
            <summary>查看冻结原文</summary>
            <p className="copy-text">{review.original_text}</p>
          </details>
          <h3>目标用户画像</h3>
          {value.personas.length ? (
            value.personas.map((p) => <PersonaSummary key={p.persona_id} persona={p} />)
          ) : (
            <p className="muted">本会议未带入画像。</p>
          )}
          {value.project_context && (
            <>
              <h3>市场与品牌备注</h3>
              <p>{value.project_context.brand_notes || '未填写品牌提示'}</p>
              <p>{value.project_context.market_notes || '未填写市场背景'}</p>
            </>
          )}
          <h3>参与角色</h3>
          <ul className="role-roster">
            {value.roles.map((r) => {
              const count = value.turns.filter((t) => t.role === r).length
              return (
                <li key={r}>
                  <span className={`role-avatar ${r}`}>{roleNames[r].slice(0, 1)}</span>
                  <div>
                    <strong>{roleNames[r]}</strong>
                    <small>
                      {count === 2 ? '两轮已完成' : count ? '已完成第一轮' : '等待发言'}
                    </small>
                  </div>
                </li>
              )
            })}
          </ul>
          <p className="fine-print">上下文在发起时冻结，之后编辑项目不会改动本会议。</p>
        </aside>
        <section className="surface discussion-column">
          <div className="section-title">
            <h2>讨论流</h2>
            <Badge tone={value.status === 'completed' ? 'ok' : ''}>
              {value.status === 'completed'
                ? '已有结论'
                : value.status === 'generating'
                  ? '正在生成'
                  : '进行中'}
            </Badge>
          </div>
          <div className="host-intro">
            <span className="host-mark">主持</span>
            <div>
              <strong>围绕具体问题，让不同视角交汇</strong>
              <p>本次目标：{goals[value.goal]}。每个角色依次发言两轮，再整理共识与分歧。</p>
            </div>
          </div>
          {!value.turns.length && (
            <div className="discussion-empty">
              <span className="roundtable-symbol" aria-hidden="true">
                ◌
              </span>
              <h3>议题已就位，等待第一位角色</h3>
              <p>可直接推进，也可在下方补充主持人指令。</p>
            </div>
          )}
          {value.turns.map((turn, i) => (
            <div key={i}>
              {i % value.roles.length === 0 && (
                <div className="round-divider">
                  第 {turn.round} 轮 · {turn.round === 1 ? '提出观点' : '回应与收敛'}
                </div>
              )}
              {value.host_notes
                .filter((n) => n.before_turn === i)
                .map((note, j) => (
                  <p className="host-note" key={j}>
                    主持人指令：{note.text}
                  </p>
                ))}
              <article className={`meeting-turn ${turn.role}`}>
                <header>
                  <span className={`role-avatar ${turn.role}`}>
                    {roleNames[turn.role].slice(0, 1)}
                  </span>
                  <div>
                    <strong>{roleNames[turn.role]}</strong>
                    <small>第 {turn.round} 轮</small>
                  </div>
                  <Badge tone={turn.vote === 'disagree' ? 'risk' : ''}>{votes[turn.vote]}</Badge>
                </header>
                <p>{turn.viewpoint}</p>
                <div className="turn-proposal">
                  <strong>行动建议</strong>
                  <p>{turn.proposal}</p>
                </div>
                {turn.source_ids.length > 0 && (
                  <details>
                    <summary>引用来源 · {turn.source_ids.join(' / ')}</summary>
                    {review.sources
                      .filter((s) => turn.source_ids.includes(s.source_id))
                      .map((s) => (
                        <div className="source" key={s.source_id}>
                          <a href={s.url} target="_blank" rel="noreferrer">
                            {s.source_id} · {s.title}
                          </a>
                          <q>{s.excerpt}</q>
                        </div>
                      ))}
                  </details>
                )}
              </article>
            </div>
          ))}
          {value.status !== 'completed' ? (
            <div className="host-controls">
              <div className="section-title">
                <h3>主持人控制</h3>
                <span>
                  {value.turns.length} / {value.roles.length * 2} 次角色发言
                </span>
              </div>
              {value.error && (
                <p className="error" role="alert">
                  {value.error}
                </p>
              )}
              <label className="field">
                补充指令（可选）
                <textarea
                  rows={3}
                  maxLength={1000}
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  placeholder="例如：请重点讨论消费者会怎样理解这句承诺…"
                />
              </label>
              <button
                disabled={busy || value.status === 'generating'}
                onClick={async () => {
                  await advance(instruction)
                  setInstruction('')
                }}
              >
                {busy || value.status === 'generating' ? '正在生成…' : `推进：${next}`}
              </button>
              <small>失败时保留已完成发言，可重试当前步骤。</small>
            </div>
          ) : (
            <div className="host-finish">
              <strong>主持人已完成归纳</strong>
              <p>在右侧审阅结论后，可回写报告或提交修改稿复审。</p>
            </div>
          )}
        </section>
        <aside className="surface conclusion-column">
          <div className="section-title">
            <h2>结论区</h2>
            <span>{date(value.created_at)}</span>
          </div>
          {value.conclusion ? (
            <>
              <Conclusions value={value.conclusion} />
              {value.conclusion.source_ids.length > 0 && (
                <p className="fine-print">结论引用：{value.conclusion.source_ids.join(' / ')}</p>
              )}
              <div className="conclusion-actions">
                <button disabled={busy || value.written_back} onClick={writeback}>
                  {value.written_back ? '已回写审核报告' : '回写审核报告'}
                </button>
                <button
                  className="secondary"
                  onClick={() => {
                    setShowRecheck(!showRecheck)
                    if (!copy) setCopy(value.conclusion?.revised_copy ?? '')
                  }}
                >
                  发起复审
                </button>
                <button
                  className="secondary"
                  onClick={() => downloadJson(`圆桌纪要-${value.meeting_id}.json`, value)}
                >
                  导出会议纪要
                </button>
              </div>
              {showRecheck && (
                <form
                  className="recheck-form"
                  onSubmit={(e) => {
                    e.preventDefault()
                    recheck(copy.trim())
                  }}
                >
                  <label className="field">
                    修改后文案
                    <textarea
                      aria-label="修改后文案"
                      rows={8}
                      value={copy}
                      onChange={(e) => setCopy(e.target.value)}
                      maxLength={8000}
                      required
                      placeholder="填写经过核实的修改稿，不增加未经证实的产品事实。"
                    />
                  </label>
                  <button disabled={busy || !copy.trim()}>提交修改稿复审</button>
                  <p className="fine-print">保存为同一项目的新文案版本，保留原图与原报告。</p>
                </form>
              )}
            </>
          ) : (
            <div className="conclusion-placeholder">
              <div className="conclusion-lines" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <h3>让结论从讨论中产生</h3>
              <p>两轮发言结束后，主持人会整理共识、分歧、修改建议、待办与风险提示。</p>
              {value.turns.length > 0 && (
                <p>
                  {value.turns.filter((t) => t.vote === 'disagree').length} 次明确分歧 ·{' '}
                  {value.turns.filter((t) => t.vote === 'need_evidence').length} 次补证请求
                </p>
              )}
            </div>
          )}
          <p className="fine-print">AI 角色是模拟视角，不代表真人调研、法律意见或投放批准。</p>
        </aside>
      </div>
    </>
  )
}
