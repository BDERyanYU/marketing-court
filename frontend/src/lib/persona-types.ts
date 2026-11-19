import type { Health } from './types'

export interface Trait {
  attribute: string
  value: string
  status: 'grounded' | 'inferred' | 'unknown' | 'user_supplied'
  source_quote: string | null
}
export interface PersonaDraft {
  persona_id: string
  name: string
  traits: Trait[]
}
export interface PersonaReport {
  report_id: string
  filename: string
  mode: Health['mode']
  model: string
  personas: PersonaDraft[]
}
export interface Member {
  member_id: string
  specification?: { type: string; persona: Record<string, unknown> & { name: string } }
  name?: string
  situation?: string
  assumptions?: string[]
  persona_prompt?: string
  sampled_values: Record<string, unknown>
}
export interface PersonaPanel {
  panel_id: string
  report_id: string
  members: Member[]
  base_persona: PersonaDraft | null
  theories: { title: string; version: string; source: string }[]
  tinytroupe_plan: {
    sample_plan: { sampled_values: Record<string, unknown>; quantity: number }[]
  } | null
}
export const metrics = {
  clarity: '清晰度',
  trust: '信任',
  appeal: '吸引力',
  purchase_interest: '购买考虑',
} as const
export const votes = {
  would_consider: '愿意进一步了解',
  unsure: '不确定',
  would_pass: '略过',
} as const
export interface Reaction {
  interpretation: string
  noticed: string
  possible_misreading: string | null
  evidence_needed: string[]
  trust_reason: string
  uncertainty: string
  scores: Record<keyof typeof metrics, number>
  vote: keyof typeof votes
  vote_reason: string
}
export interface Comparison {
  comparison_id: string
  panel_id: string
  mode: Health['mode']
  original_text: string
  revised_text: string
  next_index: number | null
  total_exposures: number
  exposures: { member_id: string; variant: string; reaction: Reaction }[]
  pairs: { member_id: string; member_name: string; original: Reaction; revised: Reaction }[]
  vote_counts: Record<'A' | 'B', Record<keyof typeof votes, number>> | null
  metric_changes: Record<
    keyof typeof metrics,
    { higher: number; same: number; lower: number }
  > | null
  notice: string
}
export interface PersonaSample {
  filename?: string
  notice?: string
  report_text: string
  original_text: string
  revised_text: string
  mode: Health['mode']
  model: string
}
