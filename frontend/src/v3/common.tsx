import { useEffect, useRef, type ReactNode } from 'react'
import type { Conclusion, Persona } from './types'

export const channels: Record<string, string> = {
  general_advertising: '通用广告',
  meta: 'Meta',
  google: 'Google Ads',
  tiktok: 'TikTok',
  amazon: 'Amazon',
  website: '独立站 / 落地页',
  email: '电子邮件',
}
export const states: Record<string, string> = {
  draft: '草稿',
  reviewing: '审核中',
  decision: '待决策',
  roundtable: '圆桌中',
  concluded: '有结论',
  archived: '已归档',
}
export const goals: Record<string, string> = {
  direction: '找修改方向',
  risk: '评估风险',
  consensus: '形成共识',
  copy: '输出修改稿',
}
export const votes: Record<string, string> = {
  support: '支持方向',
  revise: '建议调整',
  disagree: '保留分歧',
  need_evidence: '需要补证',
}
export const roleNames: Record<string, string> = {
  consumer: '目标消费者代表',
  brand: '品牌方',
  legal: '法务合规',
  creative: '创意策划',
  media: '投放顾问',
  localizer: '本地化专家',
}
export const date = (value: string) =>
  new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>
}
export function Dialog({
  title,
  close,
  children,
}: {
  title: string
  close: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    ref.current?.showModal()
    return () => {
      ref.current?.close()
    }
  }, [])
  return (
    <dialog ref={ref} aria-label={title} onCancel={close} className="modal">
      <header>
        <h2>{title}</h2>
        <button className="icon-button" aria-label="关闭弹窗" onClick={close}>
          ×
        </button>
      </header>
      {children}
    </dialog>
  )
}
export function PersonaSummary({ persona }: { persona: Persona }) {
  return (
    <div className="persona-summary">
      <div>
        <strong>{persona.name}</strong>
        <Badge>v{persona.version}</Badge>
      </div>
      <p>{persona.summary}</p>
      <small>
        {persona.provenance === 'inferred_from_material'
          ? '从素材派生 · 待验证假设'
          : '用户提供 · 未经研究验证'}
      </small>
    </div>
  )
}
export function Conclusions({ value }: { value: Conclusion }) {
  return (
    <>
      {(
        [
          ['consensus', '共识'],
          ['disagreements', '分歧'],
          ['recommendations', '修改建议'],
          ['todos', '待办'],
          ['risk_notes', '风险提示'],
        ] as const
      ).map(([key, title]) => (
        <section className={`conclusion-group ${key}`} key={key}>
          <h3>{title}</h3>
          {value[key].length ? (
            <ul>
              {value[key].map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">未记录{title}</p>
          )}
        </section>
      ))}
      {value.revised_copy && (
        <section className="conclusion-group">
          <h3>建议修改稿</h3>
          <p className="copy-text">{value.revised_copy}</p>
          <small>仍需核实产品事实并复审。</small>
        </section>
      )}
    </>
  )
}
export function downloadJson(filename: string, value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }),
  )
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
