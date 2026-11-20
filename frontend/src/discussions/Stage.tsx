import { useState, type CSSProperties, type ReactNode } from 'react'
import type { Discussion, Persona, Turn } from './types'
import { speakerName, speech } from './types'

const HOST: Persona = {
  id: 'moderator',
  name: '主持人',
  role: '圆桌主持',
  viewpoint: '梳理现有证据，指出共识、分歧和待核实的事实。',
  motivation: '',
  expertise: '',
  thinking_style: '',
}

function xy(index: number, total: number) {
  const x = total === 1 ? 50 : 15 + (70 * index) / (total - 1)
  return { x, y: 64 + Math.abs(x - 50) * 0.26 }
}

export function Portrait({ index, className = '' }: { index?: number; className?: string }) {
  if (index === undefined)
    return <span className={`rt-portrait rt-portrait-empty ${className}`} aria-hidden="true" />
  return (
    <span
      aria-hidden="true"
      className={`rt-portrait ${className}`}
      data-portrait-index={index}
      style={{
        backgroundPosition: `${(index % 4) * (100 / 3)}% ${Math.floor(index / 4) * (100 / 3)}%`,
      }}
    />
  )
}

export default function Stage({
  discussion,
  turn,
  children,
}: {
  discussion: Discussion | null
  turn: Turn | undefined
  children: ReactNode
}) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [focused, setFocused] = useState<string | null>(null)
  const [pinned, setPinned] = useState<string | null>(null)
  const seats = discussion ? [HOST, ...discussion.participants] : []
  const selected = seats.find((seat) => seat.id === (hovered ?? focused ?? pinned))
  const speakerIndex = seats.findIndex((seat) => seat.id === turn?.speaker_id)
  const active = speakerIndex < 0 ? null : xy(speakerIndex, seats.length)
  const stageStyle = {
    '--speaker-x': `${active?.x ?? 50}cqi`,
    '--speaker-y': `${active?.y ?? 64}cqh`,
    '--seat-span': `${70 / Math.max(1, seats.length - 1)}cqi`,
  } as CSSProperties

  return (
    <section className="rt-stage" aria-label="圆桌舞台" style={stageStyle}>
      <div className="rt-salon" aria-hidden="true" />
      {active && turn && (
        <div
          className="rt-light"
          key={turn.speaker_id}
          data-spotlight-for={turn.speaker_id}
          aria-hidden="true"
        >
          <i />
        </div>
      )}
      <div className="rt-table" role="img" aria-label="木质圆桌">
        <i />
        <span />
      </div>
      {seats.map((seat, index) => {
        const { x, y } = xy(index, seats.length)
        return (
          <button
            type="button"
            key={seat.id}
            data-seat-id={seat.id}
            data-invited={seat.id === discussion?.issue.invitee?.member_id || undefined}
            aria-label={`查看 ${seat.name} 人设`}
            aria-expanded={selected?.id === seat.id}
            className={`rt-seat${turn?.speaker_id === seat.id ? ' is-speaking' : ''}`}
            style={{ left: `${x}%`, top: `${y}%` }}
            onPointerEnter={(event) => {
              if (event.pointerType !== 'touch') setHovered(seat.id)
            }}
            onPointerLeave={() => setHovered(null)}
            onFocus={(event) => {
              if (event.currentTarget.matches(':focus-visible')) setFocused(seat.id)
            }}
            onBlur={() => setFocused(null)}
            onClick={() => setPinned((previous) => (previous === seat.id ? null : seat.id))}
          >
            <Portrait index={discussion?.avatar_indices[seat.id]} />
            <span className="rt-nameplate">
              <strong>{seat.name}</strong>
              <small>{seat.role}</small>
            </span>
          </button>
        )
      })}
      {active && turn && (
        <div className="rt-bubble" data-speaking-for={turn.speaker_id}>
          <div className="rt-bubble-content">
            <strong>
              {speakerName(turn)}{' '}
              <span>{discussion?.status === 'finished' ? '发言回放' : '正在发言'}</span>
            </strong>
            <p>{speech(turn.text)}</p>
          </div>
        </div>
      )}
      {selected && (
        <aside className="rt-persona" aria-label={`${selected.name} 的人设`}>
          <div className="rt-persona-title">
            <Portrait index={discussion?.avatar_indices[selected.id]} />
            <div>
              <strong>{selected.name}</strong>
              <small>{selected.role}</small>
            </div>
            {pinned === selected.id && (
              <button type="button" onClick={() => setPinned(null)} aria-label="关闭人设">
                ×
              </button>
            )}
          </div>
          <dl>
            {[
              ['立场', selected.viewpoint],
              ['动机', selected.motivation],
              ['专长', selected.expertise],
              ['讨论方式', selected.thinking_style],
            ]
              .filter(([, value]) => value)
              .map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
          </dl>
        </aside>
      )}
      {children}
    </section>
  )
}
