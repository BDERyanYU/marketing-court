import { useEffect, useRef } from 'react'
import { resourceUrl } from '../../lib/api'
import type { Asset, Review } from '../../lib/types'

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
    container.current
      ?.querySelector('[data-selected="true"]')
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [selectedRisk])
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
