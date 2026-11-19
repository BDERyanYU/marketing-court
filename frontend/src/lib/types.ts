export type Page = 'setup' | 'review' | 'court'
export interface Health {
  status: string
  mode: 'demo' | 'live'
  model: string
}
export interface Project {
  project_id: string
  name: string
  market: string
}
export interface ProjectInput {
  name: string
  market: 'GB'
  product_category: 'reusable_bottle'
}
export interface Asset {
  asset_version_id: string
  project_id: string
  image_url: string
  kind: 'image' | 'copy' | 'text'
  text?: string | null
  parent_asset_version_id?: string | null
  original_filename: string
  width: number
  height: number
}
export interface Anchor {
  anchor_id: string
  text: string
  polygon: [number, number][]
  method: string
}
export interface Source {
  source_id: string
  title: string
  issuer: string
  excerpt: string
  url: string
  checked_at: string
  version: string
}
export interface Risk {
  risk_id: string
  claim_quote: string
  severity: 'high' | 'medium' | 'low'
  assessment: string
  reason: string
  source_ids: string[]
  evidence_gaps: string[]
  anchor_ids: string[]
  location_status: string
  demo_rule_ids?: string[]
}
export interface DemoCase {
  case_id: string
  title: string
  market: 'GB' | 'EU'
  category: string
  polarity: 'negative' | 'positive'
  expected_risks: number
  description: string
  provenance: string
}
export interface Review {
  review_id: string
  asset_version_id: string
  project_id: string
  mode: 'demo' | 'live'
  model: string
  original_text: string
  anchors: Anchor[]
  risks: Risk[]
  sources: Source[]
  limitations: string[]
  created_at: string
  rule_pack_version: string
  example?: DemoCase | null
  example_rules?: {
    rule_id: string
    market: string
    citation: string
    excerpt: string
    explanation: string
  }[]
}
export interface Task {
  task_id: string
  resource_id: string
  kind: 'review' | 'rewrite'
  status: 'queued' | 'running' | 'completed' | 'failed' | 'interrupted'
  stage: string
  events: string[]
  error: string | null
  result_id: string | null
}
export interface Rewrite {
  rewrite_id: string
  source_review_id: string
  source_risk_id: string
  review_id: string
  original_text: string
  revised_text: string
  removed_text: string
  reason: string
}
export interface Turn {
  step: string
  round: number
  role: 'prosecutor' | 'defense'
  position: string
  argument: string
  source_ids: string[]
  evidence_requested: string[]
}
export interface Judgment {
  disposition: string
  reason: string
  source_ids: string[]
  evidence_requested: string[]
}
export interface CourtCase {
  case_id: string
  mode: 'demo' | 'live'
  model: string
  status: string
  next_step: string | null
  snapshot: {
    market: string
    risk_id: string
    claim_quote: string
    original_text: string
    citations: { source_id: string; excerpt: string; url: string }[]
  }
  turns: Turn[]
  judgment: Judgment | null
}
