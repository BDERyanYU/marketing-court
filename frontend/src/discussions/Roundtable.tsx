import { useEffect, useRef, useState, type FormEvent } from 'react'
import Icon from '../components/Icon'
import { api, post } from '../lib/api'
import InviteePicker from './InviteePicker'
import Stage, { Portrait } from './Stage'
import type { Discussion, InviteeReference, Risk, Source, Turn } from './types'
import { speakerName, speech } from './types'
import './roundtable.css'

const ROUND_LABELS: Record<string, string> = {
  'Opening statements': '初步解读',
  'Free discussion': '交叉讨论',
  'Closing statements': '收尾与建议',
}

function roundOf(turn: Turn, index: number, roundCount: number) {
  return turn.round_index ?? (index === 0 ? 0 : Math.max(0, roundCount - 1))
}

function References({ ids, sources }: { ids: string[]; sources: Source[] }) {
  return (
    ids.length > 0 && (
      <span className="rt-citations" aria-label="引用">
        {sources
          .filter((source) => ids.includes(source.source_id))
          .map((source) => (
            <a
              href={source.url}
              key={source.source_id}
              title={source.title}
              target="_blank"
              rel="noreferrer"
            >
              {source.source_id} ↗
            </a>
          ))}
      </span>
    )
  )
}

export default function Roundtable({
  reviewId,
  risk,
  close,
}: {
  reviewId: string
  risk: Risk
  close: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const storageKey = `marketing-roundtable:${reviewId}:${risk.risk_id}`
  const [discussionId, setDiscussionId] = useState(() => sessionStorage.getItem(storageKey))
  const [discussion, setDiscussion] = useState<Discussion | null>(null)
  const [question, setQuestion] = useState('现有规则证据能否支持这项风险判断？还缺哪些材料？')
  const [invitee, setInvitee] = useState<InviteeReference | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')
  const [cursor, setCursor] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const turns = discussion?.turns ?? []
  const turn = turns[cursor]
  const roundCount = discussion?.rounds.length ?? 0
  const activeRound = turn ? roundOf(turn, cursor, roundCount) : 0
  const hasNext = cursor < turns.length - 1
  const finished = discussion?.status === 'finished'
  const canReplay = finished && !hasNext && turns.length > 0

  useEffect(() => {
    const node = dialog.current
    if (!node) return
    node.showModal()
    return () => node.close()
  }, [])

  useEffect(() => {
    if (!discussionId || finished) return
    let disposed = false
    let timer: ReturnType<typeof setTimeout>
    const controller = new AbortController()
    async function poll() {
      try {
        const update = await api<Discussion>(
          `/api/discussions/${encodeURIComponent(discussionId!)}`,
          {
            signal: controller.signal,
          },
        )
        if (disposed) return
        setDiscussion(update)
        setError('')
        if (update.status !== 'finished') timer = setTimeout(poll, 1050)
      } catch (problem) {
        if (disposed) return
        setError(problem instanceof Error ? problem.message : '无法读取讨论记录。')
        timer = setTimeout(poll, 3500)
      }
    }
    void poll()
    return () => {
      disposed = true
      controller.abort()
      clearTimeout(timer)
    }
  }, [discussionId, finished])

  useEffect(() => {
    if (!playing || !hasNext) return
    const delay = Math.min(8500, Math.max(2300, (turn?.text.length ?? 0) * 38))
    const timer = setTimeout(() => setCursor((value) => value + 1), delay)
    return () => clearTimeout(timer)
  }, [cursor, hasNext, playing, turn?.text.length])

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!question.trim() || starting) return
    setStarting(true)
    setError('')
    try {
      const record = await post<Discussion>(
        `/api/reviews/${encodeURIComponent(reviewId)}/risks/${encodeURIComponent(risk.risk_id)}/discussions`,
        { question: question.trim(), invitee },
      )
      sessionStorage.setItem(storageKey, record.discussion_id)
      setDiscussion(record)
      setDiscussionId(record.discussion_id)
      setCursor(0)
      setPlaying(true)
      setExpanded({})
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : '无法发起圆桌。')
    } finally {
      setStarting(false)
    }
  }

  function reset() {
    sessionStorage.removeItem(storageKey)
    setDiscussionId(null)
    setDiscussion(null)
    setInvitee(null)
    setError('')
    setCursor(0)
    setExpanded({})
  }

  function jump(index: number) {
    setCursor(index)
    setPlaying(false)
    if (turns[index]) {
      setExpanded((previous) => ({ ...previous, [roundOf(turns[index], index, roundCount)]: true }))
    }
  }

  const status = starting
    ? '正在组建圆桌'
    : !discussion
      ? discussionId
        ? '正在读取记录'
        : '等待发起'
      : finished
        ? discussion.end_reason === 'completed'
          ? '讨论已完成'
          : '讨论已中断'
        : '讨论中'

  return (
    <dialog
      ref={dialog}
      className="rt-room"
      aria-labelledby="rt-title"
      onCancel={(event) => {
        event.preventDefault()
        if (!starting) close()
      }}
    >
      <div className="rt-shell">
        <header className="rt-header">
          <button type="button" className="rt-back" onClick={close} disabled={starting}>
            <Icon name="back" size={17} /> 返回审核
          </button>
          <div className="rt-heading">
            <h1 id="rt-title">圆桌复核</h1>
            <p title={risk.claim_quote}>{risk.claim_quote}</p>
          </div>
          <span className="rt-state" data-meeting-status={discussion?.status} role="status">
            <i /> {status}
            {discussion?.mode === 'demo' ? ' · 演示' : ''}
          </span>
        </header>
        <div className="rt-main">
          <Stage discussion={discussion} turn={turn}>
            {!discussionId && (
              <form className="rt-setup" onSubmit={(event) => void start(event)}>
                <h2>围绕这项证据发起讨论</h2>
                <p>{risk.reason}</p>
                <label htmlFor="rt-question">你想核对的问题</label>
                <textarea
                  id="rt-question"
                  value={question}
                  maxLength={1000}
                  rows={3}
                  onChange={(event) => setQuestion(event.target.value)}
                  disabled={starting}
                  required
                />
                <InviteePicker invitee={invitee} onChange={setInvitee} disabled={starting} />
                <button type="submit" disabled={starting || !question.trim()}>
                  {starting ? '正在分配角色…' : '启动圆桌讨论'} <Icon name="arrow" size={16} />
                </button>
                {error && (
                  <p className="rt-error" role="alert">
                    {error}
                  </p>
                )}
              </form>
            )}
            {discussionId && !turn && (
              <p className="rt-stage-note" role="status">
                {error ? '正在尝试恢复连接' : discussion ? '等待主持人开场…' : '正在读取会议记录…'}
              </p>
            )}
          </Stage>
          <aside className="rt-rail" aria-label="讨论记录">
            <div className="rt-rail-head">
              <h2>
                <Icon name="file" size={18} /> 讨论记录
              </h2>
              {discussion && <span>共 {roundCount} 轮</span>}
            </div>
            {!discussion && <p className="rt-rail-empty">逐轮发言会在讨论开始后出现。</p>}
            {discussion && (
              <>
                <p className="rt-rail-question">{discussion.issue.question}</p>
                {discussion.rounds.map((label, round) => {
                  const open = expanded[round] ?? round === activeRound
                  const records = turns
                    .map((value, index) => ({ value, index }))
                    .filter(({ value, index }) => roundOf(value, index, roundCount) === round)
                  return (
                    <section className="rt-round" key={round}>
                      <button
                        type="button"
                        className="rt-round-heading"
                        aria-expanded={open}
                        onClick={() => setExpanded((previous) => ({ ...previous, [round]: !open }))}
                      >
                        <span className="rt-round-dot" />
                        <strong>
                          第 {round + 1} 轮 · {ROUND_LABELS[label] ?? label}
                        </strong>
                        <Icon name="chevron" size={14} />
                      </button>
                      {open && (
                        <div className="rt-turns">
                          {records.length === 0 && <p className="rt-rail-empty">等待发言</p>}
                          {records.map(({ value, index }) => (
                            <article
                              className={`rt-turn${index === cursor ? ' is-current' : ''}`}
                              key={index}
                            >
                              <button
                                type="button"
                                onClick={() => jump(index)}
                                data-turn-index={index}
                                aria-current={index === cursor ? 'true' : undefined}
                              >
                                <Portrait index={discussion.avatar_indices[value.speaker_id]} />
                                <span>
                                  <strong>
                                    {speakerName(value)}
                                    {value.speaker_id === discussion.issue.invitee?.member_id && (
                                      <small>数字人像</small>
                                    )}
                                  </strong>
                                  <span>{speech(value.text)}</span>
                                </span>
                              </button>
                              <References
                                ids={value.source_ids}
                                sources={discussion.issue.sources}
                              />
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  )
                })}
                {discussion.report && (
                  <details className="rt-report">
                    <summary>主持纪要</summary>
                    <p>{speech(discussion.report)}</p>
                    <References
                      ids={discussion.report_source_ids}
                      sources={discussion.issue.sources}
                    />
                  </details>
                )}
                {discussion.issue.sources.length > 0 && (
                  <details className="rt-report">
                    <summary>本次审核依据</summary>
                    {discussion.issue.sources.map((source) => (
                      <div key={source.source_id} className="rt-source">
                        <a href={source.url} target="_blank" rel="noreferrer">
                          {source.source_id} · {source.title} ↗
                        </a>
                        <p>{source.excerpt}</p>
                      </div>
                    ))}
                  </details>
                )}
              </>
            )}
            {discussionId && (error || discussion?.error) && (
              <p className="rt-error" role="alert">
                {error || discussion?.error}
              </p>
            )}
            {discussionId && (finished || (!discussion && error)) && (
              <button type="button" className="rt-reset" onClick={reset}>
                发起新讨论
              </button>
            )}
          </aside>
        </div>
        {discussion && (
          <footer className="rt-controls" aria-label="发言播放控制">
            <ol className="rt-timeline">
              {discussion.rounds.map((label, index) => {
                const first = turns.findIndex((value, i) => roundOf(value, i, roundCount) === index)
                return (
                  <li key={index}>
                    <button
                      type="button"
                      disabled={first < 0}
                      aria-current={index === activeRound ? 'step' : undefined}
                      onClick={() => jump(first)}
                    >
                      <i /> <span>{ROUND_LABELS[label] ?? label}</span>
                    </button>
                  </li>
                )
              })}
            </ol>
            <div className="rt-transport">
              <button
                type="button"
                onClick={() => jump(cursor - 1)}
                disabled={cursor === 0}
                aria-label="上一条发言"
              >
                ‹
              </button>
              <button
                type="button"
                className="rt-play"
                onClick={() => {
                  if (canReplay) {
                    setCursor(0)
                    setExpanded({})
                    setPlaying(true)
                  } else {
                    setPlaying((value) => !value)
                  }
                }}
                disabled={turns.length === 0}
                aria-label={canReplay ? '重新播放' : playing ? '暂停播放' : '继续播放'}
              >
                {playing && !canReplay ? 'Ⅱ' : '▶'}
              </button>
              <button
                type="button"
                onClick={() => jump(cursor + 1)}
                disabled={!hasNext}
                aria-label="下一条发言"
              >
                ›
              </button>
              <span>
                {turn ? cursor + 1 : 0} / {turns.length}
              </span>
            </div>
          </footer>
        )}
      </div>
    </dialog>
  )
}
