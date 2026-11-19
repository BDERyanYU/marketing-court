import { useEffect, useRef } from 'react'
import { resourceUrl } from '../lib/api'
import type { Asset, Review } from '../lib/types'

export default function AssetCanvas({
  asset,
  review,
  selectedRisk,
  onSelect,
}: {
  asset: Asset
  review: Review | null
  selectedRisk: string
  onSelect: (id: string) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (asset.kind === 'text') {
      const element = container.current
      const selected = element?.querySelector<HTMLElement>('[data-selected="true"]')
      if (element && selected) {
        const frame = element.getBoundingClientRect()
        const bounds = selected.getBoundingClientRect()
        if (bounds.top < frame.top || bounds.bottom > frame.bottom) {
          element.scrollTop += bounds.top - frame.top - 20
        }
      }
      return
    }
    container.current?.querySelector('[data-selected="true"]')?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'nearest',
    })
  }, [selectedRisk, asset.kind])
  if (asset.kind === 'text') {
    const text = review?.original_text ?? asset.text ?? ''
    const ranges = (review?.risks ?? [])
      .map((risk) => ({ risk, start: text.indexOf(risk.claim_quote) }))
      .filter((item) => item.start >= 0)
      .sort((a, b) => a.start - b.start)
    const pieces = []
    let cursor = 0
    for (const { risk, start } of ranges) {
      if (start < cursor) continue
      pieces.push(text.slice(cursor, start))
      pieces.push(
        <button
          key={risk.risk_id}
          className={`text-risk ${risk.risk_id === selectedRisk ? 'selected' : ''}`}
          data-selected={risk.risk_id === selectedRisk}
          aria-label={`查看风险：${risk.claim_quote}`}
          aria-pressed={risk.risk_id === selectedRisk}
          onClick={() => onSelect(risk.risk_id)}
        >
          {risk.claim_quote}
        </button>,
      )
      cursor = start + risk.claim_quote.length
    }
    pieces.push(text.slice(cursor))
    return (
      <div className="text-asset" ref={container}>
        <p className="text-asset-label">
          {asset.parent_asset_version_id
            ? '改写文案版本'
            : review?.example
              ? '案例原始文案'
              : '提交的广告文案'}
        </p>
        <div className="text-asset-content" lang="en">
          {pieces}
        </div>
        <p className="text-asset-note">
          {review?.risks.length ? '点击标记句，查看对应风险与依据。' : '未标出待核查句。'}
        </p>
      </div>
    )
  }
  return (
    <div className="asset-scroll" ref={container}>
      <div className="asset-canvas" style={{ aspectRatio: `${asset.width}/${asset.height}` }}>
        <img src={resourceUrl(asset.image_url)} alt={asset.original_filename} />
        {review && (
          <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-label="风险定位标注">
            {review.risks.flatMap((r) =>
              review.anchors
                .filter((a) => r.anchor_ids.includes(a.anchor_id))
                .map((a) => (
                  <polygon
                    key={`${r.risk_id}-${a.anchor_id}`}
                    points={a.polygon.map(([x, y]) => `${x * 1000},${y * 1000}`).join(' ')}
                    className={r.risk_id === selectedRisk ? 'selected' : ''}
                    data-selected={r.risk_id === selectedRisk}
                    role="button"
                    tabIndex={0}
                    aria-label={`查看风险：${r.claim_quote}`}
                    onClick={() => onSelect(r.risk_id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onSelect(r.risk_id)
                      }
                    }}
                  >
                    <title>{r.claim_quote}</title>
                  </polygon>
                )),
            )}
          </svg>
        )}
      </div>
    </div>
  )
}
