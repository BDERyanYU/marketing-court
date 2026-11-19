import type {
  Asset,
  DemoCase,
  Health,
  Project as BaseProject,
  Review as BaseReview,
  Task,
} from '../lib/types'
export type { Asset, DemoCase, Health, Task }
export type Page =
  'projects' | 'project' | 'personas' | 'meetings' | 'meeting' | 'library' | 'settings'
export interface Project extends BaseProject {
  product_category: string
  channel: string
  created_at: string
}
export interface Context {
  persona_ids: string[]
  language: string
  brand_notes: string
  market_notes: string
  archived: boolean
}
export interface Persona {
  persona_id: string
  family_id: string
  version: number
  name: string
  summary: string
  market: string
  needs: string[]
  concerns: string[]
  provenance: string
  source_review_id?: string
  created_at: string
}
export interface Review extends BaseReview {
  audience_context?: { context: Context; personas: Persona[] }
  audience_fit?: { status: string; reason: string; suggestions: string[] } | null
}
export interface Role {
  role_id: string
  name: string
  focus: string
}
export interface Turn {
  role: string
  round: number
  viewpoint: string
  proposal: string
  vote: string
  source_ids: string[]
}
export interface Conclusion {
  consensus: string[]
  disagreements: string[]
  recommendations: string[]
  todos: string[]
  risk_notes: string[]
  revised_copy: string | null
  source_ids: string[]
}
export interface Meeting {
  meeting_id: string
  project_id: string
  review_id: string
  project_name: string
  title: string
  roles: string[]
  goal: string
  issue_ids: string[]
  market: string | null
  channel: string
  personas: Persona[]
  project_context: Context | null
  review_snapshot: Review
  turns: Turn[]
  conclusion: Conclusion | null
  host_notes: { before_turn: number; text: string }[]
  status: string
  error: string | null
  mode: string
  model: string
  written_back: boolean
  created_at: string
}
export interface Addendum {
  addendum_id: string
  meeting_id: string
  review_id: string
  conclusion: Conclusion
  created_at: string
}
export interface Summary {
  project: Project
  status: string
  review_count: number
  meeting_count: number
}
export interface Detail {
  decisions: Record<string, string>
  project: Project
  context: Context
  status: string
  reviews: Review[]
  assets: Asset[]
  meetings: Meeting[]
  tasks: Task[]
  personas: Persona[]
  addenda: Addendum[]
}
export const emptyContext: Context = {
  persona_ids: [],
  language: '英语',
  brand_notes: '',
  market_notes: '',
  archived: false,
}
