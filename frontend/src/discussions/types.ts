import type { Review } from '../lib/types'

export type Risk = Review['risks'][number]
export type Source = Review['sources'][number]

export interface Persona {
  id: string
  name: string
  role: string
  viewpoint: string
  motivation: string
  expertise: string
  thinking_style: string
}

export interface Turn {
  speaker_id: string
  speaker_name: string
  speaker_kind: 'agent' | 'moderator' | 'user'
  round_index: number | null
  text: string
  source_ids: string[]
}

export interface Discussion {
  discussion_id: string
  mode: 'demo' | 'live'
  status: 'setup' | 'running' | 'paused' | 'finished'
  end_reason: 'completed' | 'stopped' | 'error' | null
  participants: Persona[]
  avatar_indices: Record<string, number>
  rounds: string[]
  turns: Turn[]
  report: string | null
  report_source_ids: string[]
  error: string | null
  issue: {
    question: string
    sources: Source[]
  }
}

export const speakerName = (turn: Turn) =>
  turn.speaker_kind === 'moderator' ? '主持人' : turn.speaker_name

export const speech = (text: string) =>
  text
    .replace(/\s*\[source:[^\]]+\]/gi, '')
    .replace(/^Question for the audience:/im, '留给你的问题')
    .trim()
